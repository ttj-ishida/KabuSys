# Changelog

すべての注記は Keep a Changelog のフォーマットに準拠しています。  
リリース日はコードベース内の __version__（0.1.0）および現時点（2026-03-31）に基づいています。

## [Unreleased]
特になし。

## [0.1.0] - 2026-03-31

### 追加 (Added)
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージ宣言とエクスポート (__init__.py) を含む基本構成。
- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み（OS 環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプション）。
  - .env パーサ実装（コメント、export 形式、シングル/ダブルクォートとエスケープ対応）。
  - Settings クラスを通じたアプリケーション設定の取得（J-Quants / kabu API / Slack / DB パス / 監視閾値 / env/log_level 判定など）。
  - 必須環境変数未設定時は ValueError を送出する _require() 実装。
- AI モジュール (kabusys.ai)
  - news_nlp: ニュース記事を OpenAI（gpt-4o-mini、JSON Mode）でバッチ評価し ai_scores テーブルへ書き込む機能。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）と UTC 変換。
    - 記事の銘柄別集約、トークン過膨張対策（最大記事数・最大文字数）。
    - バッチ送信（最大 20 銘柄/チャンク）、再試行（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）。
    - レスポンスの厳密なバリデーション（JSON 抽出、results 配列、code/score 検証、スコアクリップ）。
    - DB への冪等書き込み（DELETE → INSERT、部分失敗時に他銘柄の既存スコアを保護）。
  - regime_detector: ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込む機能。
    - ma200_ratio 算出（ルックアヘッドバイアス防止のため target_date 未満のデータのみ使用）。
    - マクロキーワードによるニュース抽出、LLM によるマクロセンチメント評価（gpt-4o-mini、JSON Mode）。
    - API 呼び出しの再試行・バックオフ、フェイルセーフ（API 失敗時は macro_sentiment = 0.0）。
    - レジームスコア合成およびラベル判定（bull / neutral / bear）。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時の ROLLBACK）。
  - 両モジュールとも OpenAI API キーが未設定の場合に明示的な ValueError を返す。
  - テスト容易性のため _call_openai_api をモジュール内で定義し patch による差し替えを想定。
- データモジュール (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理と営業日判定ロジック（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB の market_calendar を優先し、未登録日は曜日ベースでフォールバック。
    - 夜間バッチ更新 job（calendar_update_job）: J-Quants API から差分取得・バックフィル・健全性チェック・保存。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult データクラス（ETL 実行結果の集約、品質問題とエラー管理、辞書変換ユーティリティ）。
    - 差分取得・保存・品質チェック方針の設計。
    - テーブル存在確認、最大日付取得ユーティリティ（※下記「既知の問題」参照）。
  - jquants_client の利用を想定した差分取得/保存の仕組み（実装ファイルは参照されるが本差分では省略）。
- 研究モジュール (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR、相対 ATR）、流動性（20 日平均売買代金・出来高比率）、バリュー（PER / ROE）を DuckDB クエリで計算。
    - データ不足時は None を返す設計、計算は prices_daily / raw_financials のみ参照。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns: 複数ホライズン対応、入力バリデーション）。
    - IC（Spearman のランク相関）計算（calc_ic: 欠損除外・3 銘柄未満で None）。
    - ランク変換（rank: 同順位は平均ランク、丸めで ties 回避）。
    - 統計サマリー（factor_summary: count/mean/std/min/max/median）。
  - kabusys.research.__init__ で主要関数を再エクスポート。
- 実装方針・品質設計上の注記（コード全体に一貫）
  - ルックアヘッドバイアス回避のため、datetime.today()/date.today() を内部計算で直接参照しない設計（関数に target_date を注入）。
  - DuckDB を用いた SQL と Python の混合処理によるデータ処理。
  - DB 書き込みは冪等性を重視（DELETE → INSERT、ON CONFLICT 方針、トランザクション制御）。
  - OpenAI 呼び出しは失敗時に安全にフォールバックする（例外を上位へ伝播しない設計が多い）。
  - ロギングを適切に配置（情報、警告、例外ログ）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の問題 (Known issues)
- kabusys.data.pipeline._get_max_date の実装がファイル末尾で途切れている（`return date.fro` のような不完全な箇所を確認）。  
  - 影響: テーブルの最大日付取得ユーティリティが正しく動作しない可能性がある。ETL の差分範囲計算に影響する恐れ。  
  - 対策: 該当関数の実装を修正し、最大日付を正しく date 型で返す処理に置き換えてください（単体テスト追加推奨）。
- 一部の外部クライアント実装（jquants_client 等）は本差分で参照されているが、リリースに含まれるかは実際のパッケージ配布状況に依存します。ETL や calendar_update_job の実行前に依存クライアントが存在することを確認してください。

### セキュリティ (Security)
- OpenAI API キーや各種トークンは環境変数から取得する設計。必ず安全な手段で管理してください（.env はローカル専用、コミットしないこと）。

---

注記:
- 本 CHANGELOG は提供されたソースコードから推測できる変更点・実装内容に基づいて自動作成しています。実際のリリースノートとして使用する場合は、リリース日時・追加機能・修正内容・既知の問題点をプロジェクトの実際の履歴・コミットログと照合のうえ調整してください。