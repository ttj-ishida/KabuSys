# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

全リリース一覧
- 未リリース: Unreleased
- [0.1.0] - 2026-03-31

## [Unreleased]
（現在のところ未リリースの変更はありません）

## [0.1.0] - 2026-03-31

初期公開リリース。日本株自動売買システム「KabuSys」のコア機能群を実装します。以下はコードベースから推測される主要な追加点・設計方針・挙動のサマリです。

### 追加
- パッケージ基礎
  - パッケージ名: kabusys、バージョン: 0.1.0
  - 公開モジュール群: data, strategy, execution, monitoring（__all__ 指定）

- 設定管理
  - 環境変数・設定管理モジュール (kabusys.config)
    - .env / .env.local の自動ロード（プロジェクトルート検出: .git または pyproject.toml を起点）
    - 読み込み優先度: OS環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能
    - .env パーサ実装（export 形式・シングル/ダブルクォート・エスケープ・コメント処理対応）
    - Settings クラスを公開（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等の必須取得メソッド、duckdb/sqlite/pid ファイルパス、閾値、環境/ログレベル検証）
    - env/log_level の検証（有効値集合を定義）

- AI（自然言語処理）関連
  - kabusys.ai パッケージ
    - news_nlp.score_news
      - raw_news/news_symbols を元に銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）へバッチ送信し、ai_scores テーブルへ書き込み
      - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して利用（calc_news_window 実装）
      - バッチ・トリム制御: 最大記事数・最大文字数、1チャンク最大銘柄数の制限
      - レスポンス検証・クリッピング（±1.0）、部分書き換え（DELETE → INSERT）で冪等性を確保
      - リトライ/バックオフ戦略（429/ネットワーク断/タイムアウト/5xx を対象）
      - API 呼び出し箇所はテスト容易性のため差し替え可能（_call_openai_api を patch 可能）
    - regime_detector.score_regime
      - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を算出・market_regime テーブルへ書き込み
      - ma200_ratio 計算、マクロニュース抽出（キーワードベース）、OpenAI 呼び出し、スコア合成、閾値判定、冪等 DB 書き込みを実装
      - API エラー時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）
      - OpenAI クライアント生成は引数経由または環境変数 OPENAI_API_KEY を使用
      - 同様に _call_openai_api は独立実装でモジュール結合を避ける設計

- データ（Data Platform）
  - kabusys.data パッケージの一部実装
    - calendar_management
      - market_calendar テーブルを使った営業日判定・前後営業日検索・期間内営業日の取得・SQ 判定を提供
      - DB データが無い/未登録日は曜日ベース（土日非営業）でフォールバック
      - calendar_update_job: J-Quants API からカレンダー差分取得 → market_calendar に冪等保存（バックフィル、健全性チェック実装）
    - pipeline / etl
      - ETLResult データクラス公開（ETL 結果の集約: 取得件数・保存件数・品質問題・エラーメッセージ等）
      - ETL パイプラインの設計方針に関する記述（差分更新・品質チェック・バックフィル等）
      - 複数ユーティリティ関数（テーブル存在確認、最終日取得など。途中までの実装が含まれる）

- リサーチ（Research）
  - kabusys.research パッケージ
    - factor_research
      - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（DuckDB SQL を利用）
      - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率を計算
      - calc_value: PER / ROE を raw_financials と prices_daily から計算
      - 設計方針: DuckDB 接続を受け、外部 API にアクセスしない、結果は (date, code) ベースの辞書リストで返す
    - feature_exploration
      - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを計算
      - calc_ic: スピアマンのランク相関（IC）を計算
      - rank: 同順位は平均ランクを与えるランク実装（丸めによる ties 回避）
      - factor_summary: 各カラムの count/mean/std/min/max/median を計算

### 変更
- （初版のため過去の変更はなし。設計上の重要ポイントとして下記を明記）
  - ルックアヘッドバイアス防止: 各種機能で datetime.today() / date.today() を直接参照しない設計（target_date パラメータを明示的に受け取る）
  - DuckDB 互換性を考慮したクエリ・executemany の取り扱い（空パラメータの回避等）
  - LLM 呼び出しは JSON Mode を利用し、レスポンスの厳密な JSON 出力を期待するプロンプトを採用

### 修正（バグ修正）
- リリース時点での既知のバグ修正履歴は無し（初期公開）

### パフォーマンス / 信頼性
- 冪等性の考慮: market_regime / ai_scores などの DB 書き込みは DELETE → INSERT または ON CONFLICT 相当で冪等保存を行う
- API 呼び出しのリトライ/バックオフ戦略を導入し、一時的障害を吸収
- データ不足・API 失敗時はフォールバック（例: ma200_ratio が十分なデータを得られない場合は中立値 1.0、macro_sentiment は 0.0）

### テスト支援 / 拡張性
- OpenAI API 呼び出し箇所は内部関数（_call_openai_api）として切り出しており、unittest.mock.patch による差し替えが可能
- 設定の自動ロードはプロジェクトルート検出に基づくため、配布後やテスト環境での制御用フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意

### セキュリティ
- API キー / トークン類は環境変数で必須（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）
- .env の自動読み込みは既存 OS 環境変数を保護するため protected キーセットを保持している（.env.local による上書きは OS 環境変数を変更しない）

### 既知の注意点 / 制約
- DuckDB 固有のバインド挙動や executemany の制約を考慮した実装（空 params の扱いに注意）
- OpenAI SDK の例外型変化（status_code の有無）に対する互換処理あり
- 一部ファイルで実装が途中の箇所（例: pipeline モジュールの末尾に未完の行が存在）を検出（今後の整備が必要）

---

メンテナンスや今後のリリースで記載する項目の例:
- 新しい AI モデル/プロバイダの追加
- ETL の自動スケジューラやモニタリング統合
- ストラテジー実行モジュール（strategy / execution）の具体的な実装・取引 API 連携
- 単体テスト / CI の追加、型注釈の厳格化、ドキュメント整備

もし特定のモジュールや関数について詳細な説明や、別フォーマット（英語版、CHANGELOG の日付修正など）が必要であれば指示してください。