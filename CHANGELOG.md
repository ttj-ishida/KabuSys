# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録しています。  
このファイルでは、コードベースから推測される機能追加・設計方針・既知の制約などを記載しています。

なお日付はパッケージの __version__ に合わせた初回リリース日として 2026-04-03 を使用しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-04-03

### Added
- パッケージの初期リリース (kabusys 0.1.0)
  - パッケージルート: src/kabusys/__init__.py にバージョン定義と公開モジュール一覧を追加。

- 環境変数・設定管理モジュールを追加 (kabusys.config)
  - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
  - 複雑な .env パース処理を実装（export プレフィックス、クォート内のバックスラッシュエスケープ、行コメントの取り扱い等）。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 必須値取得用 _require と Settings クラスを提供。
  - 設定項目（例）:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）、SQLITE_PATH（監視 DB）
    - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
    - CPU/MEMORY/DISK の監視閾値（% 指定）
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI 関連モジュールを追加 (kabusys.ai)
  - news_nlp: ニュース記事を集約して OpenAI（gpt-4o-mini）でセンチメントスコアを算出し ai_scores テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC 変換済み）
    - バッチ処理（最大 20 銘柄／API 呼び出し）、1 銘柄あたり記事数・文字数上限を設定
    - JSON Mode を使った厳格パース + レスポンスバリデーションを実装
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ
    - API 呼び出し箇所はテスト置換可能（_call_openai_api を patch しやすい設計）
    - DuckDB の executemany の制約に配慮した安全な DB 書き込み（部分書き換え戦略）
  - regime_detector: ETF（1321）の 200 日移動平均乖離と news_nlp によるマクロセンチメントを重み合成して市場レジーム（bull/neutral/bear）を判定し market_regime に冪等書き込み
    - MA とマクロセンチメントの重み付け（MA 70% / マクロ 30%）
    - OpenAI の呼び出し失敗時は macro_sentiment=0.0（フェイルセーフ）
    - ルックアヘッドバイアス回避のため、target_date 未満のデータのみ参照する設計

- データ処理モジュールを追加 (kabusys.data)
  - calendar_management: JPX カレンダー（market_calendar）管理 / 営業日ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）および夜間バッチ更新 job（calendar_update_job）
    - DB 未取得時は曜日ベースでフォールバック（週末は非営業日）
    - DB 登録値優先、未登録日は曜日フォールバックで一貫した挙動
    - 最大探索日数やバックフィル・健全性チェックを実装
  - pipeline / ETLResult: ETL パイプラインの結果型（ETLResult）を公開
    - ETL 実行のフェーズ別取得数、品質問題、エラーの集約を表現

- リサーチ用モジュールを追加 (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の計算
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率の計算
    - calc_value: PER / ROE（raw_financials から最新値取得）
    - DuckDB の SQL ウィンドウ関数を利用した一貫した実装（prices_daily / raw_financials のみ参照）
  - feature_exploration:
    - calc_forward_returns: 将来リターン（horizons 指定可）
    - calc_ic: ランク相関（Spearman）ベースの IC 計算（rank ユーティリティ含む）
    - factor_summary: 基本統計量 (count/mean/std/min/max/median)
    - rank: 同順位は平均ランクで扱うランク変換

- 共通実装・設計上の配慮
  - DuckDB を主要な永続化バックエンドとして利用（多くの関数が DuckDB 接続を引数に取る）
  - ルックアヘッドバイアス対策: datetime.today() / date.today() を直接参照しない設計を各所で採用（target_date を明示的に渡す）
  - DB 書き込みは冪等性を重視（DELETE → INSERT、トランザクションと ROLLBACK ハンドリング）
  - OpenAI 呼び出し: 再試行／バックオフ／エラー区分（5xx / 非5xx）に基づく扱い
  - ロギングを充実（INFO/DEBUG/WARNING/exception ログ）

### Changed
- 初回リリースのため該当なし（設計方針・実装上の決定をドキュメント化）

### Fixed
- 初回リリースのため該当なし

### Security
- OpenAI API キー・他シークレットは環境変数経由で扱う設計（Settings を介して取得）。.env 自動ロード機能はあるが、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
- 注意事項: AI 機能（news_nlp/regime_detector）を利用するには OPENAI_API_KEY の設定が必須。キー未設定時は ValueError を送出して明示的に失敗する。

### Known limitations / Notes
- 多くの処理は所定の DuckDB テーブル（prices_daily / raw_news / news_symbols / ai_scores / market_regime / raw_financials / market_calendar 等）が存在することを前提としている。スキーマは別途定義される必要あり。
- news_nlp / regime_detector は gpt-4o-mini をデフォルトモデルとして使用。モデル・パラメータは将来的に変更の余地あり。
- OpenAI レスポンスのパースは堅牢化しているが、LLM の出力形式が完全に期待通りでない場合はスコアをスキップまたは 0 にフォールバックする挙動を取る（フェイルセーフ）。
- DuckDB の executemany に関するバージョン差異（0.10 の挙動）に配慮した実装を行っている。
- 一部の計算結果はデータ不足時に None を返す（例: ma200_dev には 200 行以上が必要）。

### Removed
- 初回リリースのため該当なし

---

もし CHANGELOG の粒度（モジュールごとに細分化する、コミット単位で記載する等）を変更したい場合や、実際のリリース日・追加のリリースノート項目（既知のバグ一覧、互換性注意点など）を追記したい場合は指示してください。