# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
本リリースはパッケージ初期実装（v0.1.0）をコードベースから推測してまとめたものです。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-04-03

### 追加 (Added)
- パッケージ全体
  - 初期リリース。パッケージ名: kabusys、バージョン: 0.1.0。
  - モジュール構成を公開: data, strategy, execution, monitoring（src/kabusys/__init__.py）。

- 環境設定・初期化 (src/kabusys/config.py)
  - .env および .env.local をプロジェクトルートから自動読み込みする仕組みを追加。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - プロジェクトルートは .git または pyproject.toml を基準に __file__ から探索（CWD 非依存）。
  - .env パース機能を実装:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント扱いの仕様（クォート有無での挙動差）。
  - 環境変数取得ヘルパーを実装（Settings クラス）。
    - J-Quants / kabu / LINE / DB / 監視 / システム設定などのプロパティを用意。
    - 必須項目（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）の未設定時は ValueError を送出。
    - 環境（KABUSYS_ENV）・ログレベル（LOG_LEVEL）のバリデーションを実装。
    - パス系は Path として返却（expanduser 対応）。

- AI / ニュース NLP (src/kabusys/ai/news_nlp.py, src/kabusys/ai/__init__.py)
  - ニュース記事の銘柄別センチメント分析機能を実装（score_news）。
    - 対象ウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB と比較）。
    - raw_news と news_symbols を結合して銘柄ごとに最新記事を集約（最大記事数・文字数でトリム）。
    - OpenAI（gpt-4o-mini）へバッチ送信（1 API コールで最大 20 銘柄）。
    - JSON Mode を使ったレスポンス検証・バリデーション実装。
    - リトライ戦略（429・ネットワーク断・APITimeout・5xx）を指数バックオフで実装。
    - スコアは ±1.0 にクリップ。取得済みコードのみ ai_scores テーブルに置換（DELETE → INSERT、部分失敗時に既存データを保護）。
    - テスト用に OpenAI 呼び出しを差し替え可能（関数を patch 可能）。
  - calc_news_window ユーティリティを提供（UTC naive datetime を返却）。

- AI / 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジームを判定する score_regime を実装。
    - MA の計算は target_date 未満のデータのみを使用しルックアヘッドを排除。
    - マクロニュースは news_nlp.calc_news_window と raw_news をキーによってフィルタ。
    - OpenAI 呼び出しは gpt-4o-mini、JSON 出力を期待、失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコア（-1〜1）を閾値により bull / neutral / bear に分類。
    - market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。
    - API 呼び出しのリトライ・エラーハンドリング（RateLimitError, APIConnectionError, APITimeoutError, APIError）を実装。

- 研究用 / ファクター・特徴量探索 (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算。
    - calc_volatility: 20日 ATR、ATR の相対値、20日平均売買代金、出来高比などを計算。
    - calc_value: raw_financials を用いて PER / ROE を計算（target_date 以前の最新財務データを使用）。
    - DuckDB の SQL + ウィンドウ関数を活用した再現性のある実装（営業日ベースの窓、データ不足時は None）。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン後の終値から将来リターンを計算（horizons の検証あり）。
    - calc_ic: Spearman（ランク相関）に基づく IC 計算を実装（3 件未満で None を返す）。
    - rank: 同順位は平均ランクにするランク変換を実装（丸めで ties の検出精度確保）。
    - factor_summary: count / mean / std / min / max / median を計算する統計サマリを実装。
  - research パッケージは主要ユーティリティを再エクスポート（zscore_normalize 等）。

- データプラットフォーム (src/kabusys/data/)
  - calendar_management.py:
    - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - DB の登録値優先、未登録日は曜日ベースのフォールバックを一貫して適用。
      - 夜間バッチ更新 calendar_update_job を実装（J-Quants クライアントを通じた差分取得、バックフィル、健全性チェック）。
  - pipeline.py:
    - ETL の設計に基づく ETLResult データクラスを実装（取得数・保存数・品質問題・エラーを集約）。
    - テーブル存在チェック、最大日付取得等のユーティリティ（差分取得のための基盤）。
  - etl.py:
    - ETLResult を再エクスポートして公開インターフェースを提供。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 削除 (Removed)
- （初期リリースのため該当なし）

### 既知の設計上の注意点 / 動作仕様
- ルックアヘッドバイアス回避: 主要な関数（score_news, score_regime, factor計算等）は内部で datetime.today() / date.today() を参照せず、引数の target_date に依存する。
- API フェイルセーフ: OpenAI 呼び出し失敗時や API レスポンスパース失敗時は例外を上位に投げず（もしくは部分的にフォールバック）処理を継続する設計。ただし、API キーが未設定の場合は ValueError を送出。
- DB 書き込みの冪等性: 一貫して既存レコードの置換（DELETE → INSERT や ON CONFLICT）を意識した実装。
- DuckDB 互換性: executemany に空リストを渡すと失敗する点を考慮したガードがある（空リストの場合は呼ばない）。
- OpenAI クライアント呼び出し箇所はテストで差し替え可能（ユニットテストを想定）。

--- 

補足:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートやユーザー向けドキュメントと差異がある可能性があります。必要であれば、実際の変更履歴やリリース日、著者情報を反映して更新してください。