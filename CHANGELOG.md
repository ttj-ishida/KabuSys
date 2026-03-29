# Changelog

すべての重要な変更をこのファイルに記録します。  
このファイルは「Keep a Changelog」形式に準拠しています。  

注: 本CHANGELOGはリポジトリ内のソースコードを読み解き推測して作成したものであり、実際のコミット履歴とは異なる場合があります。

## [0.1.0] - 2026-03-29

初回公開リリース。日本株自動売買システムのコアモジュール群を提供します。主な機能、設計方針、既知の動作や注意点を以下にまとめます。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（version = 0.1.0）。
  - public サブパッケージ: data, strategy, execution, monitoring をエクスポート。

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルートを .git または pyproject.toml を基準に探索（__file__ を起点に探索するため CWD に依存しない）。
  - .env のパースは以下に対応:
    - 空行・コメント（#）を無視
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - クォート無しの場合、コメント判定は '#' の直前が空白/タブのときのみ
  - 自動ロードの優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供（プロパティ経由で J-Quants / kabuステーション / Slack / DB パス / 環境モード / ログレベル等を取得）。
  - 必須環境変数未設定時には ValueError を投げるヘルパー `_require`。

- データ層 (kabusys.data)
  - ETL パイプライン基盤（kabusys.data.pipeline.ETLResult を公開）。
  - カレンダー管理モジュール（calendar_management）:
    - market_calendar テーブルを元に営業日判定、前後営業日検索、期間内営業日列挙を提供。
    - カレンダー未取得時は曜日ベース（土日非営業）でフォールバック。
    - calendar_update_job により J-Quants から差分取得 → 冪等保存（バックフィルや健全性チェックあり）。
  - ETL 用ユーティリティ（差分取得、保存、品質チェックのための ETLResult）。

- 研究・ファクター (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、平均売買代金、出来高比率を計算。
    - calc_value: PER（EPS が無効な場合は None）と ROE を計算（raw_financials を参照）。
    - 各関数は DuckDB 接続を受け取り、prices_daily / raw_financials のみを参照。
  - feature_exploration:
    - calc_forward_returns: 指定 horizon（例: 1,5,21） に対する将来リターンを計算（LEAD を使用）。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算（None 値やデータ不足に対処）。
    - rank: 平均ランク方式（同順位は平均ランク）でランク付け。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
  - 研究用関数は外部ライブラリに依存せず標準ライブラリ/SQLのみで実装。

- AI（自然言語処理）モジュール (kabusys.ai)
  - news_nlp:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へ送信して銘柄別センチメントを算出。
    - バッチ処理（最大 20 銘柄／API 呼出）とリトライ（429/ネットワーク/タイムアウト/5xx を対象とした指数バックオフ）を実装。
    - レスポンスのバリデーションとスコアの ±1.0 クリッピングを行う。
    - スコアは ai_scores テーブルに冪等的に書き込み（対象コードのみ DELETE → INSERT）。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch でモック可能）。
    - ニュース収集ウィンドウは JST 基準（前日 15:00 ～ 当日 08:30、内部は UTC naive で扱う）。
  - regime_detector:
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
    - calc_ma200_ratio でデータ不足時に中立(1.0)を採用するフェイルセーフ。
    - マクロニュースはニュースのタイトルをキーワードでフィルタ（デフォルトのキーワード群あり）。
    - OpenAI 呼び出しは独立実装で、失敗時は macro_sentiment = 0.0 で継続。
    - 判定結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - テスト用に _call_openai_api を差し替え可能。

- ロギング & エラー処理
  - 多くの処理で詳細なログを出力（INFO/DEBUG/WARNING/EXCEPTION）。
  - データ不足や API エラー時は基本的に例外を投げずフェイルセーフ（ログ出力して中断せず継続）する処理を多用。
  - ただし DB 書き込み中の例外は ROLLBACK を試み上位へ伝播。

### Changed
- （初版のため「変更」はありません）

### Fixed
- （初版のため「修正」はありません）

### Removed
- （初版のため「削除」はありません）

### Security
- OpenAI API キーは引数で注入可能（api_key）／環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示的にエラーになる。
- .env 自動読み込み時に OS 環境変数を protected として上書きされないよう配慮。

### Notes / Usage 備考
- 必要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD / KABU_API_BASE_URL（kabuステーション）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知）
  - OPENAI_API_KEY（AI 機能を使う場合）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動ロードを無効化可能
- デフォルト DB パス
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で上書き可）
  - SQLite (monitoring 用): data/monitoring.db（環境変数 SQLITE_PATH で上書き可）
- DuckDB テーブル前提
  - 多くの関数は特定テーブル（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials, market_regime など）を参照／更新する前提。実行前に適切なスキーマ作成が必要。
- ルックアヘッド防止設計
  - AI スコアリングやレジーム判定、ファクター計算はすべて target_date を受け取り、内部で datetime.today()/date.today() を直接参照しない設計になっている（バックテストでのリーク防止）。
- テスト性
  - OpenAI API 呼出しエントリポイントは内部で抽象化されており、テスト時には unittest.mock.patch 等で差し替え可能。
- 既知の制約
  - DuckDB のバージョン差異（executemany の空リストバインド等）に配慮した実装を行っているが、環境差異で問題が発生する可能性あり。
  - OpenAI SDK の将来の変更（例: APIError の属性名等）をある程度想定した防御コードを実装しているが、互換性に注意。

### Migration / Breaking changes
- 初版リリースのため破壊的変更はありません。

### TODO / 今後の改善候補（抜粋）
- unit/integration テストの充実（DB スキーマを含むテストフィクスチャ整備）。
- エラーハンドリングや再試行ロジックのさらなる細分化（リトライ可能性の判断など）。
- レスポンスパースの堅牢化（LLM 出力のフォールバック解析を強化）。
- 監視・メトリクス（Prometheus 等）やエラーレポーティングの追加。

---

今後のリリースでは機能追加や改善をこの CHANGELOG に追記していきます。