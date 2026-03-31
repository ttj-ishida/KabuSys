# CHANGELOG

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
以下は与えられたコードベースから推測して作成した変更履歴（初回リリース想定）です。

## [Unreleased]

## [0.1.0] - 2026-03-31
初回公開リリース。日本株自動売買システムのコアライブラリを提供します。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__、バージョン 0.1.0）。
  - サブモジュール公開: data, strategy, execution, monitoring を __all__ に設定。

- 設定・環境変数管理
  - 環境変数読み込みモジュールを実装（kabusys.config）。
    - プロジェクトルートを .git または pyproject.toml から自動検出し、.env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - export 形式やクォート、エスケープ、行内コメント等に対応する堅牢な .env パーサ実装。
    - OS 環境変数を保護する機能（protected set）や override の挙動を提供。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル等をプロパティで取得・バリデーション。

- AI（ニュースNLP・レジーム判定）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出。
    - JST ベースの時間ウィンドウ計算を実装（前日 15:00 JST ～ 当日 08:30 JST に対応、内部は UTC naive datetime）。
    - バッチ処理（最大 20 銘柄/回）、記事数・文字数のトリム、JSON Mode の応答バリデーション、スコアの ±1.0 クリップ。
    - API 障害時の指数バックオフリトライ、429/ネットワーク断/タイムアウト/5xx を考慮したリトライ実装。
    - レスポンスパースの堅牢化（余計な前後テキストから JSON 抽出等）。
    - DB 書き込みは冪等性を考慮し、部分失敗時に他銘柄の既存データを消さない DELETE→INSERT の実装。
    - 公開 API: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して日次レジーム（bull / neutral / bear）を判定。
    - マクロニュース抽出（マクロキーワード一覧）→ OpenAI による JSON レスポンス取得 → 合成スコア算出。
    - API 呼び出しのリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0）実装。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。
    - 公開 API: score_regime(conn, target_date, api_key=None)

- データプラットフォーム（DuckDB ベース）
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルを用いた営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した判定ロジック。
    - 夜間バッチジョブ calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新。バックフィル・健全性チェック実装。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult dataclass を提供し、ETL の取得件数・保存件数・品質チェック結果・エラーを集約して返却。
    - 差分更新・最終取得日の算出、バックフィル、品質チェック（quality モジュール利用想定）などの方針を実装。
    - DuckDB 用ユーティリティ（テーブル存在確認、最大日付取得など）を実装。
  - jquants_client を通じたデータ取得/保存フローを想定（jq モジュール参照ポイントあり）。

- リサーチ（因子・特徴量探索）
  - factor_research モジュール
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（prices_daily を SQL ベースで取得）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から直近財務データを取得して PER/ROE を算出（EPS が 0 または欠損の場合は None）。
    - 全て DuckDB クエリで完結。データ不足時は None を返す設計。
  - feature_exploration モジュール
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。ホライズンの検証あり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（有効レコードが 3 件未満なら None）。
    - rank: 同順位は平均ランクを返すランク関数（丸めによる ties 対応あり）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出（None 値は除外）。

### 変更 (Changed)
- 設計方針・安全策の明文化（コードコメントとして）
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計が各所で採用。
  - OpenAI 呼び出し関数はモジュール毎に独立実装し、テスト時に差し替えられるよう設計（patch 可能）。

### 修正 (Fixed)
- DB 書き込み時のトランザクション処理を堅牢化（例外時に ROLLBACK、ROLLBACK の失敗は警告ログで通知）。

### 注意事項 / 動作上の留意点
- OpenAI API を利用する関数（score_news, score_regime）は api_key 引数または環境変数 OPENAI_API_KEY による認証を必要とする。未設定時は ValueError を送出。
- .env 自動ロードはプロジェクトルート (.git または pyproject.toml) を基準とするため、配布後やテスト環境での挙動に注意。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB に対する executemany に空リストを渡せない制約（DuckDB 0.10 等）を考慮して、空チェックを行ってから executemany を呼び出す実装にしている。
- AI モデルは gpt-4o-mini を想定し、JSON mode を利用して厳格な JSON 応答を期待する。ただしレスポンスの不正や余分なテキストに対する復元処理も実装済み。
- マクロニュースのキーワードや重み、閾値（MA 重み 0.7、マクロ重み 0.3、牛・熊閾値等）はコード内定数として固定されているため、将来のチューニングで定数化の改修が必要になる可能性あり。

### 非互換/破壊的変更 (Removed/Deprecated)
- なし（初回リリース）。

### セキュリティ (Security)
- 特になし（ただし API キーや機密情報は .env 等で管理する想定）。

---

この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノート作成時は、テスト結果、ドキュメント、および変更履歴（コミットログ）に基づき追記・修正してください。