# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
このリポジトリの初期バージョンとして、以下を v0.1.0 にまとめています（コードから推測して記載）。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-29
初回リリース。日本株自動売買プラットフォームのコア機能群を実装。

### Added
- パッケージ基盤
  - パッケージエントリポイント `kabusys` を定義。__version__ = "0.1.0"。
  - サブパッケージの公開: data, strategy, execution, monitoring。

- 設定・環境変数管理 (`kabusys.config`)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルート検出は .git または pyproject.toml を基準）。
  - OS 環境変数を保護する読み込みロジック（`.env.local` は上書き可能、`KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロード無効化）。
  - .env パーサ実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理対応）。
  - 設定オブジェクト `Settings` を追加（J-Quants / kabu / Slack / DB パス / 環境判定 / ログレベル検証など）。
  - 必須環境変数未設定時は明示的なエラーを送出する `_require`。

- AI 関連機能 (`kabusys.ai`)
  - ニュースセンチメントスコアリング (`news_nlp.score_news`)
    - 前日15:00 JST～当日08:30 JST（UTC で変換）のウィンドウを対象に、raw_news と news_symbols を集約して銘柄単位のテキストを作成。
    - OpenAI（gpt-4o-mini）へバッチ送信（1回最大20銘柄）し、JSON Mode で厳密にレスポンスを受け取る設計。
    - バッチ内部で記事トリム（最大記事数・最大文字数）やレスポンスバリデーション（JSON抽出、resultsキー、コード整合、スコア数値化）を実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx について指数バックオフでリトライし、失敗時は安全にスキップ（フェイルセーフ）。
    - ai_scores テーブルへの冪等更新（対象コードを限定して DELETE → INSERT）により部分失敗時の保護を実現。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え（patch）可能。

  - 市場レジーム判定 (`ai.regime_detector.score_regime`)
    - ETF 1321 の 200日移動平均乖離（重み70%）と、マクロ経済ニュースの LLM センチメント（重み30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定。
    - マクロキーワードで raw_news のタイトルを抽出し、LLM（gpt-4o-mini）へ投げて macro_sentiment を算出。
    - API リトライ（5xx・ネットワーク等）・JSONパース失敗時は macro_sentiment=0.0 にフォールバック。
    - レジーム合成スコアはクリップされ、market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実施。
    - API キー注入可能（引数 or 環境変数 OPENAI_API_KEY）。モジュール間の結合を避ける設計（OpenAI 呼び出し関数はニュース NLP と別実装）。

- データプラットフォーム・ETL (`kabusys.data`)
  - ETL 結果を表す `ETLResult` データクラスを公開（pipeline.ETLResult を再エクスポート）。
  - ETL パイプライン基盤 (`data.pipeline`)
    - 差分取得、バックフィル、品質チェック、idempotent 保存（jquants_client 経由）を想定した設計ドキュメント実装。
    - DuckDB 上での最大日付取得ユーティリティなどを実装。

  - マーケットカレンダー管理 (`data.calendar_management`)
    - market_calendar を用いた営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job による J-Quants からの差分取得と冪等保存（バックフィル・健全性チェック含む）。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算群を実装:
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（calc_momentum）
    - Volatility / Liquidity: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率（calc_volatility）
    - Value: PER・ROE（raw_financials から最新財務データを取得）（calc_value）
  - 特徴量探索・評価ツール:
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンに対応、入力検証あり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関。
    - 統計サマリー（factor_summary）とランク変換ユーティリティ（rank）。
  - データ取得は DuckDB 上の prices_daily / raw_financials のみ参照し、外部システムに影響を与えない設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 環境変数の読み込みで OS 環境を上書きしないデフォルト動作を採用。`.env.local` による上書きは許容するが OS 環境変数は保護される。
- OpenAI API キーは引数で注入可能で、環境変数依存を緩和しテスト時の安全な差し替えを支援。

### Performance
- ニュース NLP は銘柄バッチ処理で API コール回数を削減（最大20銘柄/コール）。
- DuckDB を活用したウィンドウ/集計処理でスケールを考慮した設計。

### Internals / Notes
- ルックアヘッドバイアス対策: 各 AI / リサーチ関数は datetime.today() / date.today() を内部参照せず、必ず引数の target_date を基準に処理。
- DB 書き込みは可能な限り冪等（DELETE→INSERT や ON CONFLICT）で実装し、部分失敗時のデータ保護を意識。
- OpenAI 呼び出し部分やタイムアウト／リトライは明示的に設計されており、テストのため差し替え可能。

---

今後の改善候補（推測）
- strategy / execution / monitoring の実装拡張（現状はパッケージ公開のみ）。
- より詳しいログとメトリクス（Prometheus 等）への出力。
- エンドツーエンドの統合テストと CI/CD の整備。
- ai モデルの比較・キャッシュ・コスト最適化。

---

（注）本 CHANGELOG は提供コードの内容から推測して作成したものであり、実際のコミット履歴とは異なる場合があります。必要であれば、より細かいコミット単位の履歴を生成するために追加の情報（コミットログやリリースノートの要望）を提供してください。