# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。  
日付はコミット/リリース相当としてコードベースから推測して付与しています。

注: この CHANGELOG はコード内容から実装・設計意図を推測して作成しています。実際のリリースノートとして利用する場合は必要に応じて修正してください。

## [Unreleased]

- 今後の予定（検討中・実装候補）
  - テストカバレッジの追加（ユニットテスト / 統合テスト、特に OpenAI 呼び出し回りと DuckDB 操作）
  - ドキュメント整備（API 使用例、データベーススキーマ、ETL 実行手順）
  - CI / CD パイプラインの整備（自動テスト・静的解析）
  - エラーハンドリング・監視の強化（より詳細なメトリクス・アラート）
  - jquants_client のモック／抽象化を強化してテスト容易性向上

---

## [0.1.0] - 2026-03-29

初期リリース相当。日本株自動売買システムのコアライブラリを提供する最初のバージョン。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージ公開 API として data / strategy / execution / monitoring を __all__ に定義。

- 設定管理（kabusys.config）
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - .env パーサを実装（`export KEY=val` 形式、クォート文字・バックスラッシュエスケープ、インラインコメントの扱い等に対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を実装。
  - 環境変数取得ユーティリティ Settings を実装（必須キーチェック、デフォルト値、値検証）。
  - 主要設定:
    - JQUANTS_REFRESH_TOKEN (必須)
    - KABU_API_PASSWORD (必須)
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須)
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパス）
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）

- データ関連（kabusys.data）
  - calendar_management
    - JPX カレンダー管理ユーティリティを追加。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day 等の営業日判定関数を実装。
    - market_calendar の有無に応じた DB 優先ロジックと曜日フォールバックを採用。
    - calendar_update_job: J-Quants からの差分取得と idempotent な保存（fetch/save の呼び出し、健全性チェック、バックフィル）。
  - pipeline / ETLResult
    - ETLResult データクラスを公開（ETL の実行結果集約）。
    - ETL パイプライン設計に基づくユーティリティ（最終取得日の判定、テーブル存在チェック等）を実装。
  - etl モジュールは ETLResult を再エクスポート。

- 研究（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離の計算を実装（prices_daily テーブル参照）。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率等の計算を実装。
    - calc_value: raw_financials からの EPS/ROE を用いた PER/ROE 計算を実装（target_date 以前の最新財務データを取得）。
  - feature_exploration
    - calc_forward_returns: 任意ホライズンの将来リターンを一括で計算。
    - calc_ic: スピアマンランク相関（IC）を計算（欠損・同値処理あり）。
    - rank: 同順位は平均ランクを返すランク関数。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算。
  - これらは DuckDB 接続を受け取り、外部 API には依存しない設計。

- AI（kabusys.ai）
  - news_nlp
    - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）の JSON モードで銘柄ごとのセンチメントスコアを算出して ai_scores テーブルへ書き込む処理を実装。
    - calc_news_window: 前日 15:00 JST ～ 当日 08:30 JST を対象とするウィンドウ計算（UTC naive datetime を返す）。
    - バッファリング、最大記事数・文字数制限、バッチ処理（最大 20 銘柄 / 回）、レスポンス検証、数値クリップ（±1.0）を実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフを実装。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みは部分更新（対象 code のみ DELETE → INSERT）で部分失敗時に既存データを保護。
  - regime_detector
    - score_regime: ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロニュース抽出はニュース NLP のウィンドウ計算を利用（calc_news_window から window を取得）。
    - OpenAI 呼び出しは専用実装（news_nlp 実装と共有しない）で、API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフを採用。
    - リトライと 5xx 処理、JSON パースエラーハンドリング、ロギングを実装。
    - ルックアヘッドバイアス防止のため date.today() 等は参照せず、target_date ベースでデータを絞る設計。

- 外部依存／技術選定
  - DuckDB を主要なオンディスク分析 DB として使用（prices_daily / raw_news / market_calendar / ai_scores / raw_financials 等を想定）。
  - OpenAI SDK（Chat Completions）を利用（モデル gpt-4o-mini、JSON mode を利用する想定）。
  - jquants_client（kabusys.data.jquants_client）への呼び出しを前提とした構成。

### Changed
- （該当なし／初期リリースのため変更履歴なし）

### Fixed
- （該当なし／初期リリースのため修正履歴なし）

### Removed
- （該当なし）

### Deprecated
- （該当なし）

### Security
- （該当なし）

---

注記（設計上の重要なポイント）
- ルックアヘッドバイアス回避: AI モジュールとリサーチ関数はすべて target_date を明示的に受け取り、内部で現在時刻を参照しない設計。DB クエリも target_date 未満 / 排他条件等で将来データを参照しないように注意している。
- フェイルセーフ: OpenAI 呼び出しや外部 API 失敗時は極力例外を投げず（あるいは局所的に取り扱い）、パイプライン全体が停止しないように設計されている（ただし、API キー未設定等の初期条件は ValueError を送出）。
- DuckDB の executemany の制約を考慮した実装（空リスト渡し回避など）。
- .env パーサは多くのシェルスタイルをサポートするが、特殊ケースは想定外の振る舞いとなる可能性があるため運用時は .env.example に従うこと。

---

開発・運用に関する問い合わせや、不足しているリリース情報の補完が必要な場合は知らせてください。必要に応じて日付や変更内容の修正、より詳細なリリースノートへの展開を行います。