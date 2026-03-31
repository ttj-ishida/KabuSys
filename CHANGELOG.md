CHANGELOG
=========

すべての変更は Keep a Changelog のフォーマットに準拠して記載しています。
バージョン番号はパッケージ内部の __version__（0.1.0）に合わせています。

Unreleased
----------

- なし

0.1.0 - 2026-03-31
------------------

Added
- パッケージの初期リリースとして多数のモジュールを追加
  - パッケージ公開: kabusys パッケージを追加、__all__ を通じて主要サブパッケージを公開（data, strategy, execution, monitoring）。
    - ファイル: src/kabusys/__init__.py
- 環境設定読み込み/管理機能
  - .env / .env.local ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - export KEY=val 形式やシングル/ダブルクォート、エスケープ、コメント処理に対応する堅牢な .env パーサ実装。
  - 自動読み込みを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数対応。
  - Settings クラスを提供し、必要な環境変数の取得・バリデーションを行う (JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等)。
  - DUCKDB/SQLite のデフォルトパスや環境（development/paper_trading/live）・ログレベルの検証ロジックを実装。
    - ファイル: src/kabusys/config.py
- ニュース・NLP（AI）パイプライン（OpenAI 統合）
  - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）へ送信し、センチメントスコアを ai_scores テーブルへ書き込む機能を実装。
    - タイムウィンドウ計算（JSTベース→UTC換算）、記事トリム（最大記事数/文字数）、チャンクバッチ処理、JSON mode を利用した堅牢なレスポンス処理、スコアの ±1.0 クリップ等を含む。
    - API の一時障害（429/接続断/タイムアウト/5xx）に対して指数バックオフでリトライし、最終的に失敗しても例外を投げずスキップする設計。
    - テスト容易化のため _call_openai_api を差し替え可能（unittest.mock.patch を想定）。
    - ファイル: src/kabusys/ai/news_nlp.py
  - マクロニュースとETF（1321）の200日移動平均乖離を組み合わせて市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等的に書き込む機能を実装。
    - ma200 比率とマクロセンチメント（LLM評価）の重み付け合成、スコア閾値によるラベル付け、DBトランザクションによる冪等保存を実装。
    - API失敗時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ設計。
    - ファイル: src/kabusys/ai/regime_detector.py
  - ai パッケージの公開エントリとして score_news をエクスポート。
    - ファイル: src/kabusys/ai/__init__.py
- 研究（Research）モジュール
  - ファクター計算: モメンタム（1/3/6ヶ月リターン、MA200乖離）、ボラティリティ/流動性（20日ATR、出来高比率、平均売買代金）、バリュー（PER, ROE）を DuckDB の prices_daily/raw_financials を用いて計算する関数群を追加。
    - 関数: calc_momentum, calc_volatility, calc_value
    - ファイル: src/kabusys/research/factor_research.py
  - 特徴量探索: 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ランク変換、ファクター統計サマリーを提供。
    - 関数: calc_forward_returns, calc_ic, rank, factor_summary, その他ユーティリティ
    - 設計上 pandas 等外部依存なしで純粋 Python / DuckDB で実装。
    - ファイル: src/kabusys/research/feature_exploration.py
  - research パッケージの公開エントリポイントを定義。
    - ファイル: src/kabusys/research/__init__.py
- データ（Data）プラットフォーム関連
  - マーケットカレンダー管理モジュールを追加
    - 営業日判定（is_trading_day）、前後営業日取得（next_trading_day/prev_trading_day）、期間内営業日取得（get_trading_days）、SQ日判定（is_sq_day）等を実装。
    - market_calendar が未取得の際の曜日ベースフォールバック、DB登録値優先の一貫した挙動、探索上限による安全策、カレンダー自動更新ジョブ（calendar_update_job）を実装。
    - J-Quants からの差分取得→保存処理（jquants_client を利用）とバックフィル、健全性チェックを提供。
    - ファイル: src/kabusys/data/calendar_management.py
  - ETL パイプライン（インターフェース）と ETLResult データクラスを追加
    - ETLResult により取得数・保存数・品質チェック結果・エラー概要を構造化して返却可能。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティ等を実装。
    - ファイル: src/kabusys/data/pipeline.py, src/kabusys/data/etl.py
  - data パッケージ内で jquants_client 等のクライアント利用を想定した構成。
    - ファイル: src/kabusys/data/__init__.py

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Security
- 外部 API キー（OpenAI 等）は引数経由または環境変数 OPENAI_API_KEY から取得する設計。未設定時は ValueError を発生させ明示的に扱う。

Notes / 実装上の設計判断
- ルックアヘッドバイアスの回避: 日付計算は datetime.today()/date.today() を直接参照する箇所を避け、関数呼び出し側が target_date を明示的に渡す設計を採用。
- フェイルセーフ: 外部 API 呼び出し失敗時は極力例外で全処理を停止せず、ログ記録のうえフォールバック（例: 0.0）やスキップで継続する方針。
- テスト容易性: OpenAI への実際の呼び出しを差し替え可能な設計（モジュール内の _call_openai_api を patch 可能）を用意。
- DuckDB 互換性: executemany の空リストバインド問題等 DuckDB の挙動に配慮した実装（空チェックなど）を行っている。

既知の制約 / TODO（今後の改善候補）
- PBR・配当利回りなどの一部バリューファクターは未実装（calc_value の注記）。
- strategy / execution / monitoring パッケージの具主体は本リリースでは限定的（パッケージ公開名はあるが個別実装は今後）。
- OpenAI レスポンスの多様性に対する追加バリデーションやリトライ戦略の微調整は継続課題。

お問い合わせ
- 実装や API 使用方法、DB スキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar 等）に関しては各モジュールの docstring を参照してください。