Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。リポジトリ内のコードから推測できる「注目すべき変更点／機能」をまとめています。必要に応じて日付や細部を調整してください。

CHANGELOG.md
===========

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

## [Unreleased]

## [0.1.0] - 2026-04-04
初回リリース。日本株自動売買・リサーチ用ユーティリティ群を提供します。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージ初期構成を追加。モジュール分割: data, strategy, execution, monitoring を公開。
  - パッケージバージョンを 0.1.0 に設定。

- 環境設定管理
  - kabusys.config: .env ファイルと OS 環境変数から設定を読み込む自動ロード機能を実装。
  - .env/.env.local の優先順位制御と OS 環境変数の保護（上書き禁止）に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグを追加。
  - Settings クラスを公開し、主要設定（J-Quants トークン、kabu API、LINE トークン、DB パス、監視閾値、実行環境など）をプロパティで取得可能に。

- AI（自然言語処理）モジュール
  - kabusys.ai.news_nlp: ニュース記事のセンチメント解析機能を追加。
    - raw_news + news_symbols から銘柄毎に記事を集約し、OpenAI (gpt-4o-mini、JSON mode) へバッチ送信して ai_scores テーブルへ書き込み。
    - バッチサイズ、記事数・文字数制限、JSON レスポンス検証、±1.0 でのクリップなどの仕様を実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）と指数バックオフを導入。
    - calc_news_window: ニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）算出ユーティリティを提供。
  - kabusys.ai.regime_detector: 市場レジーム判定機能を追加。
    - ETF 1321 の 200 日移動平均乖離 (重み 70%) とニュース由来の LLM マクロセンチメント (重み 30%) を合成し、日次で market_regime テーブルへ冪等書き込み。
    - OpenAI 呼び出し用の独立実装、API リトライ、フェイルセーフ（API失敗時 macro_sentiment=0.0）を導入。

- データ関連 (Data platform)
  - kabusys.data.pipeline / etl / ETLResult:
    - ETLResult データクラスを追加して ETL の取得数・保存数・品質問題・エラーを集約。
    - ETL パイプライン設計に関するユーティリティとドキュメントコメントを追加。
  - kabusys.data.calendar_management:
    - JPX マーケットカレンダー管理機能を追加（market_calendar テーブルの読み書き、営業日判定、next/prev_trading_day、get_trading_days、is_sq_day、夜間更新 job）。
    - DB 存在チェック、曜日ベースのフォールバック、最大探索日数制限、バックフィル・健全性チェック等を実装。
  - kabusys.data.jquants_client を呼び出す場所を想定した差分取得／保存フローに対応（fetch/save の呼び出しを想定）。

- リサーチ（ファクター・特徴量）
  - kabusys.research.factor_research:
    - モメンタム（1m/3m/6m、MA200乖離）、ボラティリティ（20日 ATR、ATR/株価等）、バリュー（PER、ROE）などのファクター計算を実装。
    - DuckDB を用いた SQL ベース計算で、欠損・データ不足時の扱いを仕様化（None 戻し）。
  - kabusys.research.feature_exploration:
    - 将来リターン計算（複数ホライズンに対応）、IC（Spearman rank）計算、ランク変換、ファクター統計サマリー機能を実装。
    - pandas 等に依存せず標準ライブラリ＋DuckDBで実装。

### 変更 (Changed)
- DB 操作設計
  - DuckDB の仕様差異への互換性対策を実装（executemany の空リスト回避、list 型バインドの回避など）。
  - テーブル更新は冪等性を重視（DELETE → INSERT / ON CONFLICT ポリシー想定）し、部分失敗時に既存データを保護する設計を採用。

- ロギング・監視
  - 各モジュールで詳細な情報/警告ログを追加してトラブルシュートを容易に。

- OpenAI 統合
  - gpt-4o-mini を JSON mode で利用する前提で実装。応答パース失敗時の保護処理（JSON 抽出ロジック）を追加。

### 修正 (Fixed)
- レスポンスパースの堅牢化
  - news_nlp と regime_detector での OpenAI レスポンスの JSON パース失敗時に、前後の余計なテキストから最外の {} を抽出して復元するフォールバックを追加。
  - エラー種別に応じたリトライ/フォールバック挙動を実装（RateLimitError / APIConnectionError / APITimeoutError / 5xx をリトライ、それ以外はフェイルセーフで無害化）。

- 環境変数パーザ
  - .env 行パース処理で export プレフィックス、クォート内のエスケープ、行内コメントの扱いなどを正しくサポートするよう改善。
  - 読み込み失敗時は warnings.warn を出すことでプロセスを停止させない。

### セキュリティ (Security)
- 環境変数の保護
  - 自動 .env ロード時、既存の OS 環境変数は protected として上書きを防止（.env.local は上書き優先だが OS 環境は保護）。
  - OpenAI API キーや J-Quants トークンなどの必須値が未設定の場合は ValueError を発生させる明示的チェックを提供（誤操作で無効なまま動くことを防止）。

### 注意事項 / マイグレーション
- OpenAI API
  - score_news / score_regime は OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）が必須。未設定時は ValueError が発生します。
  - LLM 呼び出しをテストする際は、内部の _call_openai_api を unittest.mock.patch で差し替えることを想定しています。

- ルックアヘッドバイアス回避
  - すべての分析／スコアリング関数は datetime.today() / date.today() を内部参照せず、呼び出し側が target_date を明示的に渡す設計です。バックテストや再現性に配慮してください。

- DuckDB 互換性
  - DuckDB のバージョン差異に依存しうる SQL やバインドの扱いに対する注意事項があります。実行環境の DuckDB バージョンは動作確認を推奨します。

---

今後のリリース案（例）
- Unreleased: 監視・実行モジュール（execution、monitoring）の実装完了／自動売買ループの追加
- Unreleased: strategy モジュールに戦略実装（バックテスト・ポートフォリオ組成）と safer order execution の導入

（必要があれば、リリース日やカテゴリの修正、追加の詳細追記を行います。）