# Changelog

すべての重要な変更点をこのファイルに記録します。  
このリポジトリでは「Keep a Changelog」のフォーマットに従います。

※ バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に合わせています。

## [0.1.0] - 初回リリース
最初の公開リリース。主にデータ取得・ETL、マーケットカレンダー、リサーチ用ファクター計算、ニュース/マクロのAIスコアリング機能および設定管理を提供します。

### 追加
- パッケージ基礎
  - パッケージメタ情報と公開モジュールのエクスポートを追加（kabusys.__init__）。
  - 型注釈と DuckDB を用いた処理を基本設計として採用。

- 環境設定（kabusys.config）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート、インラインコメントの扱い、無効行スキップ）。
  - .env/.env.local の読み込み順序（OS 環境 > .env.local > .env）と上書き制御（protected set 適用）。
  - settings オブジェクトを追加し、J-Quants / kabu API / Slack / DB パス等の取得プロパティを提供。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL など）とユーティリティプロパティ（is_live, is_paper, is_dev）を実装。

- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST の範囲）を calc_news_window で提供。
    - バッチサイズ制限、記事数/文字数トリム、JSON Mode によるレスポンス検証、レスポンス整形（前後余分テキストの {} 抽出）を実装。
    - リトライ戦略（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）を実装し、API エラーはフェイルセーフでスキップ。
    - DuckDB への冪等書き込み（DELETE → INSERT）処理を実装。部分失敗時に既存スコアを保護。
    - テストのために内部 _call_openai_api を差し替え可能な設計を採用。
    - score_news(conn, target_date, api_key=None) を公開 API として提供（戻り値: 書き込んだ銘柄数）。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - ma200_ratio 計算、マクロ記事フィルタリング、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント評価、スコア合成を実装。
    - API リトライ／フェイルセーフ（API障害時は macro_sentiment=0.0）を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - score_regime(conn, target_date, api_key=None) を公開 API として提供。

- データ基盤（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間差分更新ジョブ calendar_update_job を実装（J-Quants クライアント経由）。
    - 営業日判定ユーティリティ関数群を実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB に登録がない場合は曜日ベース（平日＝営業日）でフォールバックする挙動を採用し、DB 登録値を優先する一貫したロジックを実装。
    - 最大探索日数やバックフィル・健全性チェック等の保護ロジックを導入。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを定義し、ETL の取得数／保存数／品質問題／エラー情報を集約して返却可能に。
    - 差分取得、バックフィル、品質チェック（kabusys.data.quality）を想定した設計。
    - パイプライン用ユーティリティ（テーブル存在チェック、最大日付取得など）を実装。
    - kabusys.data.etl から ETLResult を再エクスポート。
  - jquants_client との連携を前提とした保存処理呼び出し（fetch/save）を想定。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER、ROE）を DuckDB ベースで計算する関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - 設計上、prices_daily / raw_financials のみ参照し、本番の注文系 API にはアクセスしない。
    - データ不足時の扱い（例: 必要行数未満で None を返す）を明確化。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（複数ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（スピアマンのρをランクベースで算出、有効レコードが少ない場合は None）。
    - ランク変換 util: rank(values)（同順位は平均ランク、丸め処理で ties 対応）。
    - 統計サマリー: factor_summary(records, columns)（count/mean/std/min/max/median を計算）。
    - 便利な再エクスポート: zscore_normalize（kabusys.data.stats から）を research パッケージで公開。

- ロギング・フェイルセーフ設計
  - 各モジュールで詳細なログ出力を追加（info/debug/warning/exception）。
  - DB 書き込みに失敗した場合の ROLLBACK 保護、API 呼び出し失敗時の安全なフォールバックを多数実装。

### 変更
- （初回リリースのため該当なし）

### 修正
- （初回リリースのため該当なし）

### 削除
- （初回リリースのため該当なし）

### 既知の注意点
- OpenAI API 呼び出しは gpt-4o-mini を前提としており、API キーは api_key 引数または環境変数 OPENAI_API_KEY で与える必要がある。未設定時は ValueError を送出する。
- DuckDB の executemany に対する挙動（空リスト不可など）に配慮した実装を行っているため、古い DuckDB バージョンとの互換性は考慮済みだが環境差異に注意。
- time / date の扱いは「ルックアヘッドバイアス防止」のため、target_date を明示的に渡す設計（datetime.today() を直接参照しない）。
- テスト容易性のため内部 API 呼び出し関数（例: _call_openai_api）をモックする設計になっている。

### セキュリティ
- 機密情報（API キー等）は環境変数から取得する前提。.env の自動読み込み機能は必要に応じて無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

今後の予定（例）
- データ品質チェックモジュールの実装拡張（quality の具体的チェック追加）。
- 追加ファクター（PBR、配当利回り等）や発注/実行モジュールの実装。
- ユニットテスト・統合テストの整備と CI ワークフロー追加。