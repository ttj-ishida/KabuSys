# Changelog

すべての変更は「Keep a Changelog」形式で記載し、セマンティックバージョニングに従います。日付はリリース日を示します。

## [Unreleased]
- （今後の変更をここに記載）

## [0.1.0] - 2026-04-01

### Added
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - src/kabusys/__init__.py によるパッケージ定義とエクスポート（data, research, ai, 等）。
- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - export 形式やクォート、インラインコメントのパースを考慮した .env パーサ実装。
    - OS 環境変数の保護（override/protected オプション）。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境・ログレベル等をプロパティから取得可能に。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）。
- AI モジュール
  - src/kabusys/ai/news_nlp.py
    - raw_news と news_symbols を集約して銘柄毎にニュースをまとめ、OpenAI（gpt-4o-mini）の JSON モードでバッチ評価して ai_scores テーブルへ保存する機能（score_news）。
    - タイムウィンドウ計算（JSTベース → UTC変換）、バッチサイズ制御、記事/文字トリム、最大リトライ（429/ネットワーク/5xx のエクスポネンシャルバックオフ）。
    - レスポンスバリデーション、スコアの ±1.0 クリップ、トランザクション（DELETE → INSERT）により冪等性を確保。
    - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch 可能に）。
  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離 (ma200_ratio) とマクロニュースの LLM センチメントを重み合成して日次の市場レジーム（bull/neutral/bear）を判定する機能（score_regime）。
    - prices_daily / raw_news からのデータ取得、LLM 呼び出し（独立実装）、リトライ、フェイルセーフ（API 失敗時 macro_sentiment=0.0）、および market_regime テーブルへの冪等書き込み。
    - 設計上、datetime.today() 等の直接参照はせずルックアヘッドバイアスを防止。
- Data モジュール
  - src/kabusys/data/calendar_management.py
    - JPX カレンダー管理機能（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が無い／未登録の場合は曜日ベースでフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants API から差分取得し market_calendar を冪等更新（バックフィル、健全性チェック含む）。
  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult データクラス（ETL の取得・保存件数、品質問題、エラー一覧を保持）と ETL パイプラインの基本ユーティリティを提供。quality モジュールと連携する設計。
    - テーブル存在チェックや最大日付取得などのヘルパーを実装（ETL の差分取得ロジックの基礎）。
- Research モジュール
  - src/kabusys/research/factor_research.py
    - calc_momentum, calc_volatility, calc_value: prices_daily / raw_financials を用いたモメンタム／ボラティリティ／バリューファクター計算を実装。結果は (date, code) キーの dict リストで返す。
    - 設計上、本番口座や発注 API にはアクセスしない（分析専用）。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns、calc_ic（Spearmanランク相関）、rank、factor_summary（count/mean/std/min/max/median）を実装。外部ライブラリ非依存（標準ライブラリのみ）。
  - src/kabusys/research/__init__.py による公開 API の整理。
- テスト性・堅牢性向上
  - 多くの箇所で API 呼び出しのリトライ・バックオフや例外ハンドリング、ログ出力を実装。
  - OpenAI への呼び出しは各モジュールで独立したラッパーを持ち、ユニットテスト時に差し替え可能にしている。
  - DuckDB executemany に対する互換性考慮（空リスト渡しを防ぐチェック）など DB 周りの実装上の注意を反映。

### Fixed
- ai/news_nlp.py / ai/regime_detector.py にて OpenAI API の 5xx / ネットワークエラー等に対するリトライ戦略を実装し、失敗時は局所的にフォールバック（0.0）して処理継続することでフェイルセーフ性を確保。
- raw JSON 応答に余分な前後テキストが混在するケースへ対応するため、JSON の最外の {} を抽出してパースを試みるロジックを追加（news_nlp）。

### Notes / 設計上の注記
- ルックアヘッドバイアス防止: AI / リサーチ系の関数は date 引数を受け取り、内部で datetime.today() / date.today() を直接参照しない設計になっている。
- DB 書き込みは可能な限り冪等性を保つ（DELETE→INSERT / ON CONFLICT 想定）。部分失敗時に既存データを保護するため、書き込み対象コードを限定している。
- OpenAI API キーは引数で注入可能（api_key）で、未指定時は環境変数 OPENAI_API_KEY を参照する。未設定の場合は ValueError を発生させる。

### Known issues / 既知の問題
- src/kabusys/data/pipeline.py の末尾にある _get_max_date の実装が途中で途切れているように見える（`return date.fro` のような未完成コード片）。この部分は正しく最大日付を返す実装へ修正が必要。
- 初期リリースのため、実行時に必要な DB テーブル構造（スキーマ）や外部 API（J-Quants / OpenAI / kabuステーション / Slack）への接続設定・権限等の事前準備が必要。
- DuckDB バインド型の互換性やバージョン差異による細かい挙動差（ANY 型バインドの取り扱い等）を回避するための実装上の工夫があるが、運用環境での追加検証を推奨。

### Security
- 現時点で特記すべきセキュリティ修正は無し。ただし運用時は API キー・パスワード類を .env や環境変数で安全に管理し、KABUSYS_DISABLE_AUTO_ENV_LOAD の取り扱いに注意すること。

---

（以上）