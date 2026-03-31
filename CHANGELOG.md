# CHANGELOG

すべての変更は Keep a Changelog の形式に従い、セマンティックバージョニングを使用しています。  
このファイルはコードベースからの推測に基づき作成しています。

## [Unreleased]
- 次回リリースに向けた追加・修正はここに記載します。

## [0.1.0] - 2026-03-31
初回リリース。以下の主要機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（src/kabusys/__init__.py）。
  - バージョン情報: 0.1.0。
  - 公開サブパッケージ: data, research, ai, など主要モジュール群を公開。

- 設定管理 (src/kabusys/config.py)
  - Settings クラスを実装し、環境変数ベースの設定取得インターフェースを提供。
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサーで export プレフィックス、クォート内エスケープ、行末コメント処理等に対応。
  - 主要設定プロパティを実装（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境・ログレベル検証）。
  - 必須環境変数未設定時は明確な ValueError を送出。

- AI 関連 (src/kabusys/ai)
  - ニュース NLP スコアリング (news_nlp.score_news)
    - ニュース収集ウィンドウ計算（JST の前日 15:00 ～ 当日 08:30 に対応、UTC 変換）を実装。
    - raw_news と news_symbols を用いて銘柄別に記事を集約（最大記事数/文字数でトリム）。
    - OpenAI（gpt-4o-mini）へバッチ送信（最大 20 銘柄 / チャンク）し、JSON Mode の応答をパースして ai_scores テーブルへ冪等的に書き込み。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ実装。
    - レスポンスの厳密なバリデーション、スコアの ±1.0 クリップ、部分失敗時に既存スコアを保護する差し替えロジックを実装。
    - テスト容易性のため _call_openai_api を差し替え可能（unittest.mock でモック可）。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照して MA とマクロ記事を取得、OpenAI 呼び出しでマクロセンチメントを算出。
    - API エラー発生時はマクロセンチメントを 0.0 としてフェイルセーフ処理。
    - 計算結果を market_regime テーブルへ冪等的（BEGIN/DELETE/INSERT/COMMIT）に書き込み。
    - OpenAI 呼び出しは news_nlp の内部実装と分離して実装（モジュール結合回避）。

- データプラットフォーム (src/kabusys/data)
  - マーケットカレンダー管理 (calendar_management)
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day の判定 API を実装。
    - market_calendar が存在しない場合は曜日ベース（平日＝営業日）のフォールバック。
    - calendar_update_job により J‑Quants から差分取得 → 保存（バックフィル / 先読み / 健全性チェック付き）を実装。
    - DB 登録値を優先し、未登録日は曜日フォールバックで一貫して扱う設計。

  - ETL パイプライン (pipeline.ETLResult, etl で再エクスポート)
    - ETLResult データクラスを実装し、ETL 実行のメタ情報（取得/保存数、品質問題、エラー）を格納。
    - quality チェックは検出しても ETL を中断せず呼び出し元が判断可能な設計。
    - デフォルトのバックフィル日数やカレンダー先読みなど ETL の設計方針を実装（差分取得の自動化）。

- リサーチ / ファクター計算 (src/kabusys/research)
  - factor_research：calc_momentum, calc_volatility, calc_value を実装。
    - SQL ベースで DuckDB を使い、過去データからモメンタム（1m/3m/6m 等）、MA200乖離、ATR、平均売買代金、PER/ROE などを算出。
    - データ不足時の None ハンドリングやウィンドウスキャン範囲のバッファを考慮。

  - feature_exploration：calc_forward_returns, calc_ic, rank, factor_summary を実装。
    - 将来リターンの一括取得、スピアマン IC（ランク相関）、ランク付け（同順位は平均ランク）、統計サマリー機能を提供。
    - pandas 等に依存せず純粋に標準ライブラリと SQL で実装。

### 修正 / 考慮点 (Fixed / Notes)
- DuckDB 互換性と安全策
  - DuckDB 0.10 の executemany 空リスト制約に対応（空チェックを事前実施）。
  - DuckDB からの date 型への変換ユーティリティを提供（_to_date）。
- LLM レスポンス処理の堅牢化
  - news_nlp の JSON パースは失敗時に文字列から最外側の {} を抽出して復元を試みるフォールバックを実装。
  - regime_detector / news_nlp 共に 5xx の APIError、タイムアウト、接続エラー、レート制限をリトライ対象にし、一定回数失敗したら安全にフォールバック（例: スコア=0.0）する設計。
- ルックアヘッドバイアス防止
  - 各 AI / リサーチ処理は内部で datetime.today() / date.today() を参照せず、明示的に渡された target_date と半開区間クエリ（date < target_date 等）でデータ参照を行う設計。
- .env パーサーの堅牢化
  - export プレフィックス、クォート内エスケープ、行末コメント（スペース直前の # をコメント扱い）など実用的なケースを考慮。
  - .env.local を .env より優先して上書きするロジック（OS 環境変数は保護）。

### 機能的設計メモ / 実装上の特徴
- IDempotent な DB 書き込み（ON CONFLICT / DELETE→INSERT の明示的利用）により部分失敗時のデータ保護を重視。
- テスト容易性のため OpenAI 呼び出しポイントを差し替え可能な実装にしている（単体テストでのモックが容易）。
- エラー時は例外を不用意に投げずログに落とす・フォールバックする方針（フェイルセーフ）。ただし、API キー未設定等の致命的な前提違反は ValueError を送出。
- 各モジュールは外部発注 API 等を呼ばない（分析 / データ処理に限定）、本番環境では別モジュールで実際の発注等を行う想定。

### 破壊的変更 (Deprecated / Breaking Changes)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- OpenAI API キーや各種トークンは環境変数で管理。未設定時に明示的に例外を出すことで誤動作を防止。
- .env 自動ロードは環境で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

---

注: 本 CHANGELOG は提供されたソースコードの構造・コメント・実装内容から推測して作成しています。実際のリリースノート作成時にはコミットログ・変更差分・担当者コメント等を合わせて精査してください。