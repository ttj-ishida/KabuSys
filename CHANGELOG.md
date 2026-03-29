# CHANGELOG

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

現在のバージョン: 0.1.0

## [Unreleased]
- なし（初回リリースに向けた履歴は下記 0.1.0 を参照）

## [0.1.0] - 2026-03-29
初回公開リリース。日本株自動売買プラットフォームの基盤機能を実装しました。主な追加点は以下の通りです。

### 追加
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = "0.1.0"）。
  - パッケージの公開APIとして data / strategy / execution / monitoring を __all__ に登録。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルと環境変数を扱う設定モジュールを追加。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）により、CWD に依存せず .env を自動読み込み。
  - .env のパース強化:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの取り扱い（クォートあり/なしで適切に処理）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。テスト用に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - Settings クラスを提供し、必須環境変数の検査（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_* など）、パス系のデフォルト、KABUSYS_ENV / LOG_LEVEL の検証ロジックを実装。
  - 設定取得はプロパティ経由で行い、未設定時は明確な例外メッセージを返す。

- AI（ニュースNLP / レジーム判定）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントスコアを算出して ai_scores テーブルへ保存するワークフローを実装。
    - タイムウィンドウ算出（前日 15:00 JST ～ 当日 08:30 JST の記事を対象）を calc_news_window で提供。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）・1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）を導入してトークン肥大化対策。
    - API 呼び出しでのリトライ（429／ネットワーク断／タイムアウト／5xx）に対する指数バックオフを実装。失敗時はロギングして該当チャンクをスキップ（フェイルセーフ）。
    - OpenAI レスポンスのバリデーションと JSON 復元ロジック（前後テキスト混入時に最外側の {} を抽出）を実装。スコアは ±1.0 にクリップ。
    - DuckDB へは部分的置換（DELETE → INSERT）で冪等性を確保し、部分失敗時に既存スコアを保持する設計を採用。
  - kabusys.ai.regime_detector
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とニュースベースの LLM マクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する機能を追加。
    - DuckDB から価格とニュースを取得し、OpenAI（gpt-4o-mini）を用いてマクロセンチメントを算出。API 呼び出しは専用内部実装でモジュール結合を避ける。
    - API エラーやパース失敗時は macro_sentiment=0.0 とするフェイルセーフ挙動。
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）する。

- データ基盤（Data）
  - kabusys.data.calendar_management
    - JPX カレンダー（market_calendar）を操作するユーティリティを実装。
    - 営業日判定（is_trading_day / is_sq_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内の営業日リスト取得（get_trading_days）を提供。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバックする堅牢設計。
    - calendar_update_job により J-Quants からの差分取得 → market_calendar へ冪等保存（fetch / save の例外ハンドリングを含む）を実装。バックフィルや健全性チェックを導入。
  - kabusys.data.pipeline / kabusys.data.etl
    - ETL パイプラインの基礎を実装。ETLResult dataclass を定義し、取得件数・保存件数・品質チェック結果・エラー一覧を集約して返却できるようにした。
    - 差分取得、バックフィル、品質チェックを想定した設計（外部 jquants_client、quality モジュールとの連携ポイントを用意）。
    - data.etl で pipeline.ETLResult を再エクスポート。

- リサーチ（Research）
  - kabusys.research.factor_research
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）といった定量ファクターの計算関数を実装（calc_momentum / calc_volatility / calc_value）。
    - DuckDB の SQL ウィンドウ関数を有効活用し、データ不足時は None を返す等の堅牢な挙動。
  - kabusys.research.feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（Information Coefficient）算出（calc_ic）、ランク化ユーティリティ（rank）、ファクター統計サマリ（factor_summary）を実装。
    - pandas 等に依存せず、標準ライブラリ＋DuckDBで完結する設計。
  - research パッケージの __all__ で主要関数を公開。

### 変更
- none（初回リリースのため変更履歴はなし）

### 修正（バグ修正）
- none（初回リリースのため過去のバグ修正履歴はなし）

### 既知の制限・設計上の注意
- OpenAI API の呼び出しは gpt-4o-mini（JSON Mode）を想定しているため、API レスポンスのフォーマットに依存する。SDK/モデルの将来の変更によりパースロジックの適合が必要になる場合がある。
- DuckDB のバージョン依存（executemany の空リスト扱い等）を考慮して一部ワークアラウンドを実装している。将来の DB バージョンで不要となる可能性あり。
- news_nlp / regime_detector といった AI 関連処理は外部 API の不安定化を想定してフェイルセーフ（スコア 0.0 またはチャンクスキップ）を採用しているため、API 全体の不調時にはスコアが欠落することがある。
- calendar_update_job 等は J-Quants クライアント実装（kabusys.data.jquants_client）に依存しており、実環境での API キーやレスポンス仕様に応じた確認が必要。

### セキュリティ
- 環境変数管理で OS 環境変数を保護する仕組み（.env の上書き制御）を導入。機密情報は環境変数での設定を推奨。

---

今後の予定（例）
- strategy / execution / monitoring 周りの具現化（発注ロジック、実行エンジン、モニタリング通知）
- 単体テスト・統合テストの追加、CI ワークフローの整備
- パフォーマンスチューニング（大規模データ時のクエリ最適化）
- ドキュメント整備（使用例・データスキーマ・運用ガイド）

もし特定ファイルや機能についてより詳細な変更ログ（関数ごとの変更点や設計判断の背景）を希望される場合は、対象モジュールを指定してください。