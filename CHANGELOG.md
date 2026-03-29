CHANGELOG
=========
すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

注意: 以下のリリースノートは、提供されたソースコードの内容から推測して作成しています。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-29
--------------------
初回公開リリース。

Added
-----
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開。

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索し、CWD に依存しない実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープの処理、インラインコメント処理）。
  - 環境変数読み込み時の override / protected（OS 環境変数保護）オプション。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 環境 / ログレベル等の設定プロパティを提供。
  - 設定値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と is_live / is_paper / is_dev のユーティリティを提供。
  - 必須環境変数未設定時に ValueError を投げる _require ユーティリティ。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp)
    - raw_news と news_symbols を集約し、銘柄単位にニュースをまとめて OpenAI（gpt-4o-mini）へバッチ送信してセンチメントを算出する実装。
    - 時間ウィンドウ計算（前日15:00 JST ～ 当日08:30 JST）と calc_news_window を提供。
    - チャンク処理（最大 20 銘柄/チャンク）、1 銘柄あたりの最大記事数・文字数制限、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - OpenAI の JSON Mode を利用したレスポンスバリデーション（results 配列、code と score の検証、数値チェック、±1.0 クリップ）。
    - DuckDB への冪等書き込み（DELETE → INSERT、部分失敗時に既存スコアを保護する実装）。
    - テスト時の差し替えポイント（_call_openai_api の patch 想定）を用意。

  - 市場レジーム判定 (regime_detector)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定する実装。
    - ETF データ取得、ma200_ratio 算出、マクロキーワードで raw_news をフィルタ、OpenAI（gpt-4o-mini）で macro_sentiment を算出、スコア合成／クリップ、market_regime テーブルへの冪等書き込みを実装。
    - API 呼び出しのリトライ・フェイルセーフ（API 失敗時は macro_sentiment=0.0 にフォールバック）を実装。
    - datetime.today()/date.today() を参照せず、ルックアヘッドバイアスを避ける設計。

- データプラットフォーム (kabusys.data)
  - マーケットカレンダー (calendar_management)
    - market_calendar に基づく営業日判定ユーティリティを提供（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）。
    - DB 登録値優先、未登録日は曜日（平日）ベースでフォールバックする一貫したロジック。
    - 夜間バッチ更新 job (calendar_update_job) を実装し、J-Quants から差分取得 → market_calendar へ冪等保存するフローを実現。バックフィル、健全性チェック（将来日付の異常検出）あり。
    - テーブル存在チェックや DuckDB からの date 型変換ユーティリティを実装。

  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを追加（取得件数、保存件数、品質問題、エラーなどを集約）。
    - 差分更新、バックフィル、J-Quants クライアント経由の保存、品質チェック統合を想定したパイプライン基盤を実装。
    - データベース存在チェック、市場データの最大日付取得ユーティリティ等を提供。
    - etl モジュールは ETLResult を再エクスポート。

- Research（定量研究） (kabusys.research)
  - ファクター計算 (factor_research)
    - Momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を calc_momentum で計算。
    - Volatility / Liquidity: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を calc_volatility で計算。
    - Value: raw_financials から最新財務データを取得し PER / ROE を calc_value で計算（EPS が 0/欠損時は None）。
    - 全て DuckDB（prices_daily / raw_financials）を参照し外部 API に依存しない設計。
    - 不足データに対して None を返す堅牢な実装。

  - 特徴量探索 (feature_exploration)
    - 将来リターン calc_forward_returns（任意ホライズン、horizons の検証、1 クエリで複数ホライズン計算）。
    - IC（Information Coefficient）calc_ic：スピアマンのランク相関を実装（None / 有効レコード数 < 3 の場合は None）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、浮動小数丸め対策あり）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median を計算）。
    - pandas 等に依存せず標準ライブラリのみで実装。

Other notable design choices
----------------------------
- DuckDB を主要な分析 DB として前提。DuckDB のバージョン差分（executemany の空リスト問題等）を考慮した実装。
- OpenAI 呼び出しは JSON モードを利用し、レスポンスパース失敗時は safe-fallback（0.0 やスキップ）で処理を継続する方針。
- ルックアヘッドバイアスを防止するため、関数は内部で現在時刻を参照しない設計（target_date を明示的引数で受ける）。
- モジュール間の結合を弱めるため、OpenAI 呼び出しの内部関数はモジュールごとに独立して実装（テスト用にパッチが可能）。

Changed
-------
- 初版のため該当なし。

Fixed
-----
- 初版のため該当なし。

Deprecated
----------
- 初版のため該当なし。

Removed
-------
- 初版のため該当なし。

Security
--------
- 初版のため該当なし。

参考
----
- パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0" に基づく記載です。