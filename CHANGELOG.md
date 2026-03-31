# CHANGELOG

すべての注目すべき変更点をこのファイルに記載します。本プロジェクトは Keep a Changelog に準拠しています。  

現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-31
初回公開リリース。主要モジュールの初期実装を追加しました。

### 追加 (Added)
- パッケージの基本情報
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開モジュール一覧: data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から特定）。
  - .env ファイルの行パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応）。
  - .env.local を .env より優先して上書きする挙動、OS 環境変数の保護（protected set）を実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルなどの取得とバリデーションを実装。

- AI モジュール (kabusys.ai)
  - news_nlp モジュール: ニュース記事を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出して ai_scores テーブルへ保存する処理を実装。
    - 前日 15:00 JST ～ 当日 08:30 JST のウィンドウ定義（UTC 変換）と calc_news_window を実装。
    - バッチ処理（最大20銘柄）での API 呼び出し、1銘柄あたり記事数上限・文字数トリム、JSON mode 応答のバリデーション、スコアの ±1.0 クリッピング。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフによるリトライ、API 失敗時は個別チャンクをスキップして継続するフェイルセーフ設計。
    - テスト容易性のため _call_openai_api を差し替え可能に設計。
  - regime_detector モジュール: ETF 1321（日経225連動型）の200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む処理を実装。
    - ma200_ratio の算出、マクロキーワードでのニュース抽出、OpenAI による macro_sentiment 評価、スコア合成と閾値判定、冪等な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフ。

- データモジュール (kabusys.data)
  - calendar_management モジュール:
    - JPX カレンダー管理（market_calendar）用ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定 API を提供。
    - DB データが無い場合や未登録日のフォールバックとして曜日ベース（平日）判定を採用。
    - calendar_update_job を実装し J-Quants からの差分取得と market_calendar への冪等保存（バックフィル、健全性チェック含む）を実装。
  - pipeline / ETL (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラスを実装（取得数・保存数・品質問題・エラー一覧など）。
    - 差分取得・バックフィル・品質チェックの設計方針を反映したユーティリティ実装。
    - ETLResult を etl モジュールで再エクスポート。

- リサーチ機能 (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン）、200日MA乖離、ATR（20日）、20日平均売買代金、出来高比率などの定量ファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を用いた SQL ベース実装、データ不足時の None ハンドリングを実装。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等外部ライブラリに依存せず標準ライブラリと DuckDB で実装。

- モジュールのエクスポート整理
  - ai/__init__.py、research/__init__.py 等で主要関数を __all__ による公開。

### 変更 (Changed)
- 初期設計として以下の実装方針を明確化（コード内ドキュメントとして反映）
  - ルックアヘッドバイアス回避: 各スコアリング関数で datetime.today()/date.today() を直接参照しない仕様（外部から target_date を渡す）。
  - DuckDB 互換性: executemany に空リストを渡さない保護処理や list バインドの互換性に関する考慮を追加。
  - エラーハンドリング方針: API 失敗時は例外で止めず、ログとスキップで継続する（フェイルセーフ）。ただし DB 書き込み失敗時は適切に ROLLBACK して上位へ例外を伝播。

### 修正 (Fixed)
- （初回リリースのため、実運用で想定される問題を未然に防ぐ設計上の補完を多数追加）
  - .env パーサでのクォート・エスケープ・インラインコメント処理を改善し、現実の .env フォーマットに耐性を持たせました。
  - OpenAI API 呼び出しに関するリトライ処理を細かく制御（RateLimit/Timeout/Connection/5xx などに応答）。

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）。今後のメジャー変更時はこのセクションで明示します。

### セキュリティ (Security)
- 環境変数の自動ロード時、既に存在する OS 環境変数を保護する protected set を導入し、.env で意図せずシステム環境が上書きされるリスクを軽減。
- OpenAI API キー等の必須機密情報は Settings クラス経由で取得し、未設定時は明確な例外を投げることでミス設定を早期に検出。

### 既知の制約 / 注意事項 (Known issues / Notes)
- OpenAI クライアントは外部依存（openai パッケージ）を利用。テスト時は _call_openai_api をモックする想定。
- news_nlp と regime_detector は JSON mode を期待するが、稀に余計な前後テキストが混ざる場合があるためレスポンスパースで余白検出・抽出ロジックを入れて耐性を確保。
- 時刻は基本的に UTC naive datetime を利用（news window 等）。タイムゾーン混在に注意。
- DuckDB のバージョン互換性に起因するバインド仕様差異（list バインド、executemany の空リスト不可）に対する回避実装あり。

---

今後の予定:
- strategy / execution / monitoring の具体的な注文実行やモニタリング機能の実装・統合。
- テストカバレッジ拡充（ユニットテスト・統合テスト）、CI パイプラインの追加。
- ドキュメント（ユーザーガイド、API リファレンス）整備。

（注）本 CHANGELOG は提示されたソースコードの内容から推測して作成した初期リリース向けの要約です。実プロジェクトのリリースノート作成時には、実際のコミット履歴・変更差分・影響範囲を確認の上で追記・修正してください。