CHANGELOG
=========

すべての重要な変更点を記録します。本プロジェクトは Keep a Changelog の形式に準拠しています。
安定リリースのみをここに記載し、未リリースの変更は Unreleased セクションで管理します。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- ドキュメントや内部コメントを整備（関数の設計方針・フェイルセーフ動作・ルックアヘッド回避等を明記）。
- テスト容易性のためいくつかの内部 API 呼び出しを差し替え可能に（例: OpenAI 呼び出しラッパーのパッチ化を想定）。

[0.1.0] - 2026-03-29
--------------------

Added
- 初回リリースを公開。
- パッケージエントリポイントを追加
  - kabusys.__version__ = "0.1.0"
  - __all__ に data / strategy / execution / monitoring を公開。
- 環境設定管理モジュールを追加（kabusys.config）
  - .env / .env.local の自動読み込み（優先順位: OS 環境 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .git または pyproject.toml を基準にプロジェクトルートを検出して .env を探索（CWD に依存しない）。
  - クォートされた値やエスケープシーケンス、コメントの取り扱いに対応した .env パーサーを実装。
  - OS 環境変数を保護する protected オプション（.env.local の上書き制御等）。
  - 各種必須設定を取得する Settings クラスを提供（J-Quants / kabuステーション / Slack / DB パス / 環境判定・ログレベル判定等）。
  - 環境変数の値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と is_live/is_paper/is_dev のヘルパー。

- AI モジュールを追加（kabusys.ai）
  - ニュースセンチメント分析（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して ai_scores を更新。
    - バッチサイズ・トークン肥大化対策（最大記事数・文字数トリム）。
    - JSON Mode を利用した厳密なレスポンス期待と、レスポンスの復元ロジック（余分な前後テキストの対応）。
    - レート制限(429) / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ実装。
    - スコア検証・型チェック・±1.0 クリップ。部分失敗時でも既存のスコアを消さない差し替えロジック（DELETE → INSERT、対象コード絞り込み）。
    - datetime.today()/date.today() を参照しない設計（ルックアヘッドバイアス防止）。
    - テストのための _call_openai_api の差し替え（unittest.mock.patch を想定）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）と、マクロニュース LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news を参照し、duckdb に対して冪等的に market_regime テーブルへ書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - マクロキーワードでフィルタした記事を LLM に渡して macro_sentiment を算出。API 失敗時は macro_sentiment=0.0 でフォールバック。
    - LLM 呼び出しに対するリトライ・バックオフ、JSON 解析のフェイルセーフ、結果クリッピングを実装。
    - OpenAI API キーが未提供の場合は明示的に ValueError を送出。

- Research モジュールを追加（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算関数を実装
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（データ不足時は None とする挙動）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等。
    - calc_value: raw_financials から最終財務データを取得して PER / ROE を計算。
    - DuckDB SQL を活用した効率的な計算。営業日ベースの窓・データ不足判定を考慮。
  - feature_exploration: 将来リターン計算、IC（Information Coefficient）算出、統計サマリー、ランク関数を実装
    - calc_forward_returns: 複数ホライズンに対応、horizons のバリデーション。
    - calc_ic: スピアマンのランク相関を自前実装（同順位は平均ランク、必要レコード数閾値あり）。
    - factor_summary: count/mean/std/min/max/median を算出。None と非有限値を除外。
    - rank: ties の平均ランク処理、浮動小数の丸め処理で ties 検出漏れを防止。

- Data モジュールを追加（kabusys.data）
  - calendar_management: JPX カレンダー管理・営業日判定・夜間バッチ更新を実装
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - market_calendar が無い場合の曜日ベースフォールバック（週末を非営業日扱い）。
    - 最大探索日数上限（_MAX_SEARCH_DAYS）により無限ループ防止。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィルと健全性チェックを実装。
  - pipeline & etl: ETL 用ユーティリティ
    - ETLResult データクラスを公開（kabusys.data.etl 経由で再エクスポート）。
    - 差分更新・バックフィル・品質チェック連携を想定した設計（jquants_client, quality モジュールとの連携ポイント）。
    - DuckDB のテーブル存在チェック・最大日付取得等のヘルパー実装。
    - ETL 実行結果の to_dict による品質問題のシリアライズ（監査ログ用）。

Changed
- n/a（初回リリースのため変更履歴なし）

Fixed
- n/a（初回リリースのためバグ修正履歴なし）

Security
- OpenAI API キーの取り扱い: API キーは引数で注入可能で、未設定時は明示的にエラーを発生させる場所があるため誤設定に気付きやすい設計。

Notes / Implementation details
- DuckDB をデータ層に利用する設計を前提としている（関数の引数には duckdb.DuckDBPyConnection を想定）。
- LLM 呼び出しは gpt-4o-mini をデフォルトモデルとして利用し、JSON Mode を前提としたレスポンスパースを行う。
- いくつかの内部ユーティリティ（例: _call_openai_api）や外部連携部（jquants_client）についてはテスト用に差し替え可能なように設計済み。
- ルックアヘッドバイアス防止のため、target_date パラメータを明示的に受け取り、内部で現在時刻を参照しない実装方針を徹底。

Authors
- 初期実装: kabusys 開発チーム

Acknowledgments
- 本 CHANGELOG はソースコード内の docstring・コメントおよび公開 API から推測して作成しています。実際のリリースノートとして使用する際は、必要に応じて担当者名や外部依存のバージョン固定などの追記を推奨します。