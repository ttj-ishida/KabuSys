# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

## [0.1.0] - 2026-03-31

### 追加
- 基本パッケージおよびバージョン情報を追加
  - src/kabusys/__init__.py にパッケージ名と __version__ = "0.1.0" を定義。
  - パッケージ公開モジュール: data, strategy, execution, monitoring。

- 環境設定管理モジュールを追加
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
    - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索（CWD 非依存）。
    - .env パーサ: export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
    - 自動ロードの無効化オプション: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト時の利用想定）。
    - 環境変数保護: OS 環境変数を保護する protected セットを導入して上書き制御。
    - Settings クラスを提供し、アプリケーション設定（J-Quants トークン、kabu API、Slack、DB パス、環境種別、ログレベル等）をプロパティ経由で取得可能。
    - バリデーション: KABUSYS_ENV / LOG_LEVEL の許容値チェック、必須キー未設定時に ValueError を送出。

- AI（NLP）モジュールを追加
  - src/kabusys/ai/news_nlp.py
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメントスコアを生成。
    - タイムウィンドウ計算（JSTベース → UTC変換）機能 calc_news_window を実装。
    - バッチ処理（1コール最大20銘柄）、記事数/文字数上限、レスポンスの厳密な JSON 検証、スコアの ±1.0 クリップを実装。
    - リトライ戦略: 429/ネットワーク/タイムアウト/5xx に対する指数バックオフを実装。
    - 書き込みは部分原子性を考慮（書き込み対象コードのみ DELETE→INSERT）して部分失敗時に既存データを保護。
    - DuckDB の executemany 空リスト制約への対応（空の場合は実行をスキップ）。
    - テスト容易性のため、OpenAI 呼び出し部分は差し替え可能（内部 _call_openai_api を patch 可能）。

  - src/kabusys/ai/regime_detector.py
    - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily からの MA 計算は look-ahead バイアスを防ぐため target_date 未満のデータのみを使用。
    - マクロ記事抽出、OpenAI 呼び出し（同様に gpt-4o-mini + JSON Mode）、堅牢なエラーハンドリングとリトライを実装。
    - レジーム結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から解決、未設定時は ValueError。

- リサーチ（ファクター計算・特徴量探索）モジュールを追加
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高比率）、バリュー（PER、ROE）を DuckDB SQL を用いて計算する関数群を実装:
      - calc_momentum, calc_volatility, calc_value
    - 仕様: prices_daily / raw_financials のみ参照、外部 API に依存しない。
    - 結果は (date, code) キーの dict リストとして返す。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン算出（calc_forward_returns）、IC（Information Coefficient）計算（calc_ic）、ランク化ユーティリティ（rank）、および統計サマリー（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
    - calc_forward_returns は可変ホライズンをサポートし、不正なホライズン引数に対してバリデーションを実施。

  - src/kabusys/research/__init__.py で主要関数を再公開。

- データプラットフォーム関連モジュールを追加
  - src/kabusys/data/calendar_management.py
    - JPX カレンダーを管理するマーケットカレンダー機能（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar テーブルが空の場合は曜日ベース（週末除外）でフォールバック。
    - calendar_update_job による J-Quants からの差分取得と冪等保存（fetch + save via jquants_client）の夜間バッチ処理を実装。
    - 健全性チェック（未来日付の異常検知）、バックフィルの仕組みを導入。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py
    - ETLResult データクラスを実装して ETL 実行結果を構造化（取得/保存件数、品質問題、エラー一覧など）。
    - ETL の内部ユーティリティ（テーブル存在チェック、テーブル最大日付取得、calendar の調整ヘルパー）を実装。
    - jquants_client と quality モジュールを組み合わせる設計で差分取得・保存・品質チェックを想定。

- データモジュールの公開設定を整備
  - src/kabusys/data/__init__.py を追加（パッケージ空の初期化）。

### 変更（設計上の重要ポイント）
- AI 関連 API 呼び出しはフェイルセーフ設計
  - OpenAI の失敗時は例外を上位に直接伝播させず、デフォルト中立スコア（0.0）にフォールバックする箇所を設けている（ニュース/レジーム処理の堅牢性向上）。
  - API 呼び出しは内部で明示的に retry ロジックを持ち、テスト用に差し替え可能にしている。

- ルックアヘッドバイアス対策
  - 多くの分析関数（calc_news_window, score_news, score_regime, 各ファクター計算）は内部で datetime.today() や date.today() に依存せず、外部から与えた target_date を厳密に参照するよう設計。

- DuckDB 互換性考慮
  - executemany に対する空パラメータ問題に対応（実行前に空チェックを行う）し、SQL は DuckDB のウィンドウ関数等を用いて効率的に実行。

- タイムゾーン・日付扱い
  - ニュースウィンドウは JST ベースで定義し、DB 内の raw_news.datetime は UTC として比較する（関数は UTC naive datetime を返す設計）。
  - calendar / ETL 系は date オブジェクトのみを用い、timezone の混入を避ける。

### 修正 / 安定化
- 各モジュールでのエラーハンドリングとログ出力（logger）を強化
  - DB 書き込み失敗時の ROLLBACK の試行と失敗時の警告ログ出力を追加（score_regime, score_news 等）。
  - JSON 解析失敗・不正レスポンス時のワーニングとスキップ処理を追加（news_nlp のバリデーション強化）。
  - market_calendar の NULL 値検出時に警告し、曜日ベースフォールバックへフォールバックする処理を追加。

### 既知の注意点
- OpenAI API キー必須
  - score_news / score_regime など OpenAI を使う機能は api_key 引数または OPENAI_API_KEY 環境変数の設定が必須。未設定時は ValueError を送出する。
- 一部の関数は外部モジュール（jquants_client, quality）を利用する前提
  - calendar_update_job や ETL 周りは jquants_client の fetch/save 実装に依存するため、実行環境にて該当クライアントを提供する必要がある。
- 日付の計算で calendar_update_job は内部で date.today() を使用（バッチ実行設計）。分析関数は look-ahead バイアスを避けるため target_date 指定を要求する。

### セキュリティ
- 環境変数の取り扱いに注意
  - .env 自動読み込み機能が有効な環境では、機密情報が不注意に取り込まれないよう KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化を提供。

---

今後のリリースでは、strategy / execution / monitoring パッケージの実装やドキュメントの追加、CI テストや型注釈のさらに厳格化、より詳細な品質チェックルールの追加を予定しています。