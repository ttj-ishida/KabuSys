# Changelog

All notable changes to this codebase will be documented in this file.
This project adheres to "Keep a Changelog" and uses Semantic Versioning.

## [Unreleased]


## [0.1.0] - 2026-03-27

### Added
- 初回リリース: KabuSys 日本株自動売買システムの基盤機能を実装。
- パッケージ公開情報
  - パッケージバージョン: `0.1.0`（src/kabusys/__init__.py の __version__ を反映）
  - 主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring

- 環境設定
  - 環境変数/設定管理モジュールを追加（kabusys.config）。
  - .env 自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサ: `export KEY=val` 形式、シングル/ダブルクォート（バックスラッシュエスケープ対応）、インラインコメント処理などをサポート。
  - 環境上書きの際に OS 側キーを保護する `protected` ロジックを実装。
  - Settings クラスを提供し、必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）やデフォルト値、値検証（KABUSYS_ENV, LOG_LEVEL）を行う。

- データ層（DuckDB ベース）
  - data パッケージ骨格（kabusys.data.*）。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar の読み書き・夜間更新バッチ（calendar_update_job）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録がない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - 安全策: 最大探索日数制限、バックフィル、健全性チェック等を実装。
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得、保存（jquants_client 経由の idempotent 保存）、品質チェック（quality モジュールと連携）を想定した実装。
    - ETLResult データクラス（kabusys.data.pipeline.ETLResult）を公開（kabusys.data.etl で再エクスポート）。
    - デフォルトのバックフィルやカレンダー先読みなどの運用パラメータを定義。
    - DuckDB 互換性（空の executemany 回避など）を意識した実装。

- 研究・リサーチモジュール（kabusys.research）
  - factor_research: ファクター計算機能を実装
    - Momentum: mom_1m (約1ヶ月), mom_3m, mom_6m, ma200_dev（200日移動平均乖離）
    - Volatility & Liquidity: 20日 ATR（atr_20）、相対 ATR (atr_pct)、20日平均売買代金、出来高比
    - Value: PER（price / EPS）、ROE（raw_financials からの取得）
    - 関数: calc_momentum, calc_volatility, calc_value
    - 実装方針: DuckDB SQL＋Python による一貫処理、データ不足時は None を返す
  - feature_exploration: 特徴量探索・評価ユーティリティ
    - 将来リターン計算: calc_forward_returns（horizons の柔軟指定、上限検証）
    - IC（Information Coefficient）計算: calc_ic（スピアマンのランク相関）
    - ランク関数: rank（同順位は平均ランク）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
    - 全て標準ライブラリ＋DuckDB ベースで実装（pandas 等に依存しない）
  - research パッケージの __all__ に主要関数を再公開

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのテキストを作成
    - OpenAI（gpt-4o-mini）へバッチ送信して銘柄単位のセンチメントスコアを取得
    - チャンク処理（バッチサイズ 20）、1 銘柄あたり最大記事数 10、最大文字数トリム（3000 文字）
    - JSON Mode の使用と厳格なレスポンスバリデーション（results 配列、code/score）
    - リトライ戦略: レート制限・ネットワーク断・タイムアウト・5xx に対して指数バックオフ（最大リトライ回数 3）
    - スコアは ±1.0 にクリップ。API 失敗時はそのチャンクをスキップ。全体処理後、ai_scores テーブルへ部分的に置換（DELETE → INSERT）して部分失敗から保護
    - タイムウィンドウ: JST 前日15:00〜当日08:30 を UTC に変換して DB クエリ（calc_news_window を提供）
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定
    - マクロキーワードによるニュース抽出、OpenAI（gpt-4o-mini）を用いた JSON レスポンス取得
    - レジームスコア合成・クリップ・閾値判定、結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）
    - API 呼び出し失敗時は macro_sentiment=0.0 のフェイルセーフ動作
  - ai パッケージの __all__ に score_news / score_news で用いる機能等を公開

### Changed
- （該当なし）初回リリースのため互換性変更はなし。

### Fixed
- （該当なし）初回リリースのためバグ修正履歴はなし。

### Security
- API キーの取り扱いは引数/環境変数を明示的に解決し、未設定時は ValueError を投げることで安全性を確保（OpenAI API キーは api_key 引数または OPENAI_API_KEY 環境変数）。

### Notes / 設計上の重要事項
- ルックアヘッドバイアスの防止
  - AI モジュールおよびリサーチ関数は内部で datetime.today()/date.today() を参照せず、target_date ベースでウィンドウを明示的に計算する設計。
- フェイルセーフ
  - OpenAI API の失敗時はスコアを 0.0 または該当チャンクをスキップして処理を継続する設計（例外を投げて ETL 全体を止めない）。
- DuckDB 互換性
  - executemany に空リストを渡さない等、DuckDB の挙動差異を考慮した実装。
- テスト容易性
  - OpenAI 呼び出し（内部の _call_openai_api）をユニットテストで patch できるようにモジュール設計。
- 外部依存
  - AI 呼び出しは openai SDK（OpenAI クライアント）を利用する想定。リサーチ系は外部分析ライブラリに依存しない。

もしこの CHANGELOG に追加したい詳細（例: 日付修正、より細かいリリースノート、含めるべき未記載の機能）があれば教えてください。