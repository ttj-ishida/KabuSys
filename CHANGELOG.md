# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトの初期リリース履歴をコードベースから推測して記載しています。

## [Unreleased]

（現時点のブランチ／今後の変更をここに記載）

---

## [0.1.0] - 2026-03-28

初回リリース。日本株自動売買プラットフォーム「KabuSys」のコア機能群を実装しました。主な追加内容は以下の通りです。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのバージョン定義と主要サブパッケージの公開 (__version__ = 0.1.0, __all__) を追加。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。
  - export 形式やクォート・コメントの取り扱いに対応した .env パーサ実装。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - OS 環境変数を保護するための上書き制御（protected set）。
  - 必須設定取得時に未設定なら ValueError を投げる _require ユーティリティ。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等のプロパティを定義。値検証（許容 env 値、ログレベル等）を実施。
  - デフォルトパス（duckdb / sqlite）や is_live / is_paper / is_dev の補助プロパティを追加。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を用いてセンチメントを計算する score_news 関数を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で実装。
    - バッチ（最大 20 銘柄）処理、1 銘柄あたりの最大記事数・文字数トリム、返却 JSON のバリデーション、スコアクリップ（±1.0）を実装。
    - API 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、失敗時は部分スキップ（フェイルセーフ）を採用。
    - DuckDB への冪等書き込み（該当 code の DELETE → INSERT）を実装。DuckDB の executemany 空リスト制約に注意した実装。

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定する score_regime を実装。
    - ma200 比率計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）、マクロ記事フィルタ（マクロキーワード）、OpenAI 呼び出し、スコア合成、冪等 DB 書き込みを実装。
    - API キー注入（引数または環境変数 OPENAI_API_KEY）と、API 呼び出しのリトライ・エラーハンドリング（5xx 再試行、その他はフォールバック）を実装。
    - API 呼び出し部はテストで差し替え可能（ユニットテスト用の patch を想定）。

- データ処理 (kabusys.data)
  - ETL パイプライン (kabusys.data.pipeline)
    - ETL の結果を格納する ETLResult データクラスを公開（kabusys.data.etl でも再エクスポート）。
    - 差分取得・バックフィル・品質チェックの設計方針を反映したユーティリティ関数（テーブル最大日付取得、テーブル存在チェック等）を実装。
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを参照した営業日判定・前後営業日検索・期間営業日リスト取得・SQ日判定・夜間カレンダーバッチ更新（calendar_update_job）を実装。
    - calendar_update_job は J-Quants クライアントを用いて差分取得 → 冪等保存。バックフィルと健全性チェックを実装。
    - DB 登録がない日については曜日ベースのフォールバック（週末を非営業日）を採用し、DB とフォールバック間で一貫性を保持するロジックを実装。
  - jquants_client / quality 等との連携を想定した設計（実装ファイルは別途）。

- Research（因子・特徴量探索） (kabusys.research)
  - 因子計算 (kabusys.research.factor_research)
    - モメンタム（1M/3M/6M リターン、ma200乖離）、ボラティリティ（20日 ATR / 相対 ATR）、流動性（20日平均売買代金・出来高比）、バリュー（PER, ROE）を計算する calc_momentum / calc_volatility / calc_value を実装。
    - DuckDB を用いた SQL 主導の計算で、データ不足時は None を返す等の安全設計。
  - 特徴量探索 (kabusys.research.feature_exploration)
    - 将来リターン計算 calc_forward_returns（任意ホライズンの計算・入力検証）、IC 計算 calc_ic（スピアマンランク相関）、ランク変換ユーティリティ rank、統計サマリー factor_summary を実装。
    - pandas 等に依存せず、標準ライブラリ + DuckDB で実装。

- テスト容易性・運用面の配慮
  - OpenAI 呼び出しをモジュール内 private 関数として分離し、ユニットテスト時に差し替え可能（unittest.mock.patch 対応）に設計。
  - API キーを引数で注入できる設計により環境依存性を緩和。
  - 多くの処理でルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照しない設計（テスト再現性の向上）。

### 変更 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 既知の注意点 (Known issues / Notes)
- OpenAI との接続は gpt-4o-mini に依存しており、API レスポンス形式や SDK の変更により挙動が変わる可能性があります。レスポンスパース時のリカバリ（最外の {} 抽出など）を用意していますが、将来の API 変更に対して追加対応が必要になる場合があります。
- DuckDB の executemany に空リストを渡すと問題があるため、実装中で空チェックを行っている箇所があります。将来 DuckDB の挙動が変わった場合に簡素化できる可能性があります。
- calendar_update_job など外部 API 呼び出しはネットワーク失敗時に 0 を返してスキップするフェイルセーフを採用しています。運用時は監視・再実行の仕組みを併用してください。

---

今後のリリースでは、ドキュメント、型ヒントの強化、テストカバレッジ拡充、さらに実運用に向けた監視／アラート機能（Slack 通知等）の追加を予定しています。