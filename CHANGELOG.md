CHANGELOG
=========

このファイルは Keep a Changelog の形式に準拠しています。  
セマンティックバージョニングを使用します。

Unreleased
----------

- なし

0.1.0 - 2026-04-04
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開インターフェースを定義 (src/kabusys/__init__.py)。
- 環境変数 / 設定管理 (src/kabusys/config.py)
  - プロジェクトルートを .git または pyproject.toml から探索し、自動で .env / .env.local をロードする機能を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理に対応）。
  - OS 環境変数を保護する protected ロジック（.env.local は override=True だが OS 環境変数は上書きしない）。
  - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス / 監視閾値 / ログ設定等のプロパティを読み出し。必須値未設定時は明示的にエラーを出す（_require）。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）、および is_live / is_paper / is_dev のヘルパーを提供。

- AI モジュール (src/kabusys/ai)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄ごとのセンチメント ai_score を算出・ai_scores テーブルへ書き込み。
    - JST ベースのニュース収集ウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - バッチサイズ・文字数・記事数上限、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ実装。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 構造、未知コード除外、数値チェック、スコアクリップ）。
    - DB 書き込みは部分失敗に耐える設計（該当コードのみ DELETE → INSERT）。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能に設計（_call_openai_api を patch 可能）。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321（NIKKEI ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で market_regime テーブルへ書き込み。
    - MA 計算は target_date 未満のデータのみ使用しルックアヘッドを防止。
    - マクロ記事抽出はマクロキーワードリストにマッチするタイトルを取得し、記事がある場合のみ LLM 呼出しを行う（API 失敗時は macro_sentiment=0.0 として継続するフェイルセーフ）。
    - OpenAI 呼び出しはリトライ・エラー種別ごとのハンドリングを実装し、DB への書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で行う。

- データ基盤ユーティリティ (src/kabusys/data)
  - マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
    - market_calendar テーブルを元に営業日判定・SQ判定・前後営業日探索・期間内営業日列挙を提供。
    - market_calendar が存在しない/未登録日の場合は曜日ベース（土日休業）でフォールバック。
    - next_trading_day / prev_trading_day には探索上限（_MAX_SEARCH_DAYS）を設け、安全性を担保。
    - calendar_update_job を実装し、J-Quants API（jquants_client）から差分取得・バックフィル・保存を行う。最後に sanity チェックやバックフィル日数を考慮。
  - ETL パイプライン (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult dataclass を公開し、ETL の実行結果・品質問題・エラー情報を構造化して返す。
    - 差分更新・バックフィル・API からの idempotent 保存・品質チェックの設計方針を実装するための基盤を準備（jquants_client, quality モジュールと連携することを想定）。
    - etl モジュールで pipeline.ETLResult を再エクスポート。

- リサーチ / ファクター解析 (src/kabusys/research)
  - ファクター計算群 (src/kabusys/research/factor_research.py)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR・相対 ATR）、Liquidity（20 日平均売買代金・出来高比率）、Value（PER, ROE）を DuckDB 上の SQL と Python の組合せで計算。
    - データ不足時の None 扱い、date/code ベースの結果リスト返却、ログ出力を実装。
  - 特徴量探索ユーティリティ (src/kabusys/research/feature_exploration.py)
    - 将来リターン calc_forward_returns（任意ホライズンの検証、入力検証）、IC（Spearman ランク相関）calc_ic、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB で動作するよう設計。

- テスト性・堅牢性設計
  - OpenAI 呼び出し等外部依存はモジュール内関数を patch して差し替え可能にし、単体テストを容易にする設計。
  - DB 書き込みは冪等操作（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK 管理）を基本とし、部分失敗時に既存データを保護する工夫あり。
  - ルックアヘッドバイアスを避けるため、各処理は datetime.today()/date.today() を内部で参照しないよう設計（target_date を明示的に渡す）。

Security
- 環境変数の保護: 自動ロード時は既存の OS 環境変数を保護するため .env の上書きが制限される（protected set）。
- OpenAI API キーや各種トークンは環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）で管理する想定。必須項目は Settings でチェックされ、未設定時に明示的なエラーを出す。

Notes / Migration
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（Settings のプロパティで必須判定あり）
  - OpenAI を利用する機能 (news_nlp, regime_detector) を使う場合は OPENAI_API_KEY が必要（関数引数で注入可能）。
- DuckDB スキーマ（想定テーブル）
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などが利用される。ETL / calendar_update_job 実行前に必要テーブルが存在することを確認してください。
- 自動 .env ロードの挙動
  - プロジェクトルートの検出に失敗した場合は自動ロードをスキップします（配布環境での安全策）。
  - テスト環境で自動ロードを無効にする際は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Changed
- なし（新規初期リリース）

Fixed
- なし

Deprecated
- なし

Breaking Changes
- なし（初期リリースのため互換性維持の過去バージョン無し）

開発者向け補足
- OpenAI 呼び出しは内部的に response_format={"type": "json_object"} を利用する想定で実装されていますが、挙動や SDK のバージョン差分に起因した例外処理を広めに用意しています。テスト時は各モジュール内の _call_openai_api をモックすることで外部呼び出しを回避できます。