# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-28

### Added
- 基本パッケージの初期実装を追加。
  - パッケージメタ情報: kabusys.__version__ = "0.1.0"。
  - パッケージ公開モジュール: data, strategy, execution, monitoring（__all__ にてエクスポート）。
- 環境設定モジュール (kabusys.config) を追加。
  - .env/.env.local ファイルおよび環境変数を自動で読み込む自動ロード機能（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索（CWD 非依存）。
  - 高度な .env パーサ: export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い等に対応。
  - OS 環境変数の保護（既存キー保護のための protected set）。
  - Settings クラスを提供し、必要な環境変数をプロパティ経由で取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, OPENAI_API_KEY 判定など）。
  - デフォルト値: KABUSYS_ENV（development/paper_trading/live 検証）、LOG_LEVEL（DEBUG/INFO/... 検証）、KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH。
- AI モジュール (kabusys.ai) を追加。
  - news_nlp.score_news:
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini の JSON Mode）へ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたりの記事数・文字数のトリム、レスポンス検証、スコアの ±1.0 クリップ。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフでのリトライとフェイルセーフ（失敗時はそのチャンクをスキップ）。
    - テスト用に _call_openai_api を差し替え可能（unittest.mock.patch 推奨）。
    - calc_news_window: JST ベースのニュース収集ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST を UTC 変換）。
  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み70%）とニュース LLM センチメント（重み30%）を合成して日次の市場レジーム (bull/neutral/bear) を判定し market_regime テーブルへ冪等書き込みを行う。
    - OpenAI 呼び出し用の独立実装（news_nlp と内部関数を共有しない設計）。
    - API エラーに対するリトライ・フェイルセーフ（API 失敗時 macro_sentiment=0.0）。
- Data モジュール (kabusys.data) を追加。
  - calendar_management:
    - JPX カレンダー（market_calendar）を扱うユーティリティと夜間バッチ更新 job (calendar_update_job) を実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days などの営業日判定・探索機能。
    - market_calendar が未取得または一部しかない場合の曜日ベースのフォールバック（整合性保護）。
    - API 取得 → jq.save_market_calendar による冪等保存、バックフィル/健全性チェック機能を搭載。
  - pipeline / ETL:
    - ETLResult データクラスを公開（取得件数、保存件数、品質チェック結果、エラー一覧等を含む）。
    - ETL パイプライン設計（差分取得、idempotent 保存、品質チェック、backfill の取り扱い）に対応する支援ユーティリティを実装。
- Research モジュール (kabusys.research) を追加。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算。
    - 全て DuckDB を用いた SQL ベースの実装で、ルックアヘッドバイアスを防ぐ設計。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（複数ホライズン）をまとめて取得。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算。
    - rank / factor_summary: ランク計算（同順位は平均ランク）および基本統計量を算出。
  - research パッケージから zscore_normalize（kabusys.data.stats 由来）を再エクスポート。
- テスト容易性・運用性向上のための設計上の配慮を多数追加。
  - ルックアヘッドバイアス防止: 各種処理で datetime.today()/date.today() を直接参照しない設計。
  - DB 書き込みは冪等操作（BEGIN / DELETE / INSERT / COMMIT や ON CONFLICT 相当）を使用。
  - DuckDB の executemany 空リスト制約を考慮した実装。
  - OpenAI 呼び出しは JSON モードを利用し、レスポンスの厳密な検証を実装。
  - エラー発生時は部分的に継続する（フェイルセーフ）アプローチを採用。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数読み込み時に OS 環境変数を上書きしないデフォルト挙動および保護セットを実装（意図しない上書きを防止）。

---

注記（実装上の重要ポイント）
- OpenAI API キー未指定時は ValueError を送出して早期検出する（score_news, score_regime 等）。
- API 呼び出しや JSON パース失敗は基本的に例外を上位へ投げずフェイルセーフな既定値（スコア 0.0 やスキップ）で継続することでデータ欠損による全体停止を回避。
- テストでの差し替えを想定し、内部の _call_openai_api 等は patch によりモック可能。
- .env パーサは複雑なケース（クォート内のエスケープ、export 形式、インラインコメント）に対応するため堅牢化している。

今後の予定（非確定）
- strategy / execution / monitoring の具体実装追加（現在はパッケージエクスポートのみ）。
- ai モデルの切替・設定化、より詳細な品質チェックルール追加。
- ドキュメント（Usage や API リファレンス）の拡充。