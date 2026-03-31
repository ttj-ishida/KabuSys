CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このリポジトリのバージョンはパッケージ定義 (src/kabusys/__init__.py) に合わせて 0.1.0 です。

Unreleased
----------

（なし）

0.1.0 - 2026-03-31
------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基盤機能を実装。
  - パッケージエントリポイント
    - src/kabusys/__init__.py によりパッケージ名・バージョンを公開。
  - 環境設定 / 管理
    - src/kabusys/config.py
      - .env / .env.local ファイルおよび OS 環境変数からの設定読み込みを自動化（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
      - プロジェクトルート検出は __file__ を基準に .git または pyproject.toml を探索して行うため、CWD に依存しない動作。
      - .env パーサーは export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
      - 主要設定は Settings クラスでプロパティ化（必須キーは _require で検証）。J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル等を扱う。
      - KABUSYS_ENV と LOG_LEVEL の入力値検証を実装（許容値を列挙）。
  - AI 関連
    - src/kabusys/ai/news_nlp.py
      - ニュース記事を OpenAI（gpt-4o-mini）に送り銘柄ごとのセンチメント（ai_score）を生成して ai_scores テーブルへ保存するバッチ処理。
      - JST タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を UTC に変換して DB クエリを実行。
      - 1チャンク最大 20 銘柄、1銘柄あたり最大 10 記事・3000 文字でトリム。
      - JSON Mode を利用し厳格な JSON 応答を期待。レスポンスのバリデーションとスコアの ±1.0 クリップ処理を実装。
      - 429/ネットワーク断/タイムアウト/5xx に対する指数バックオフとリトライ、失敗時はスキップして継続するフェイルセーフ設計。
      - テスト容易性のため OpenAI 呼び出し関数の差し替え（patch）を想定。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（'bull'/'neutral'/'bear'）を判定。
      - マクロキーワードで raw_news をフィルタリングし、最大 20 件を LLM に渡して macro_sentiment を算出。
      - LLM 呼び出しは独立実装（news_nlp とは共有しない）で、API エラー時は macro_sentiment=0.0 にフォールバック。
      - レジーム判定結果を market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - データ基盤（ETL / カレンダー）
    - src/kabusys/data/pipeline.py
      - ETLResult データクラスを導入し ETL 実行結果（取得数・保存数・品質問題・エラー）を収集できるようにした。
      - 差分更新、backfill の考慮、品質チェックの集約（quality モジュールとの連携）を想定した設計。
      - DuckDB に対するテーブル存在チェックや最大日付取得のユーティリティを実装。
    - src/kabusys/data/etl.py
      - pipeline.ETLResult を外部に公開するインターフェースを提供。
    - src/kabusys/data/calendar_management.py
      - market_calendar を利用して営業日判定ロジックを提供（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等）。
      - DB 登録がない場合は曜日ベース（平日を営業日）でフォールバックする一貫した挙動を実装。
      - calendar_update_job により J-Quants からカレンダーを差分取得し、バックフィルおよび健全性チェックを行って保存するジョブを実装（jquants_client 経由）。
  - リサーチ / ファクター
    - src/kabusys/research/factor_research.py
      - Momentum（1M/3M/6M、MA200乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）等、定量ファクター計算を実装。
      - DuckDB 上の SQL ウィンドウ関数を活用し、(date, code) ベースの結果リストを返す。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（任意ホライズン）、IC（Spearman の ρ）計算、ランク付けユーティリティ、ファクター統計サマリーを実装。
      - pandas 等に依存せず標準ライブラリのみで実装。
    - src/kabusys/research/__init__.py による公開 API 整理（calc_momentum 等の再エクスポート）。
  - データユーティリティ
    - src/kabusys/data/__init__.py（パッケージプレースホルダ）
  - テスト・運用面の配慮
    - OpenAI 呼び出し箇所で差し替え可能にしユニットテストを容易に。
    - DuckDB の executemany に関する空リスト制約を考慮した実装（空チェックによる回避）。
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() 参照を抑制した設計（関数に target_date を明示的に渡す方式）。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- 環境変数読み込みにおいて OS 環境を保護するため、.env の上書きを制御する protected set を使用（.env/.env.local 読み込み時）。

Notes / Known limitations
- OpenAI（gpt-4o-mini）および J-Quants API への依存がある。実行環境に API キー（OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN 等）の設定が必要。
- news_nlp/regime_detector は LLM の出力に対する堅牢化処理を行っているが、JSON パースに失敗する場合や LLM が想定外の形式を返す場合はスコアをスキップ（0.0 または該当銘柄除外）する挙動となる。
- DuckDB のバージョンに依存する挙動（list 型バインド等）に対して互換性考慮の実装を行っているが、運用環境の DuckDB バージョンによっては追加の検証が必要。
- strategy / execution / monitoring パッケージは __all__ に含まれているが、本リリースのコードスナップショットでは詳細実装は含まれていない可能性がある（将来のリリースで追加予定）。
- calendar_update_job 等は jquants_client の実装に依存し、API 側の仕様変更の影響を受ける。

もし補足してほしい箇所（例: 各モジュールごとの詳細な変更履歴、リリースノートの英語版、今後のロードマップなど）があれば教えてください。