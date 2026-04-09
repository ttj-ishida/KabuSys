Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

Unreleased
----------

- なし（初回リリースは v0.1.0）

0.1.0 - 2026-04-09
------------------

Added
- パッケージ初期実装を追加（バージョン: 0.1.0）。
- 基本パッケージエントリポイントを定義
  - src/kabusys/__init__.py: パッケージ説明と __version__、公開モジュール一覧を追加。
- 環境変数 / 設定管理
  - src/kabusys/config.py:
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする機能を実装。
    - export KEY=val 形式やクォート・エスケープ、インラインコメントのパースに対応する堅牢な .env パーサを実装。
    - 自動ロード無効化環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを実装し、J-Quants、kabuステーション、LINE、データベース、監視、システム設定等のプロパティを提供。必須変数未設定時は ValueError を送出。
    - PAPER_FILL_MODE 等の検証（有効値チェック）やパス解決（expanduser）を実装。
- AI ニュース NLP / レジーム判定
  - src/kabusys/ai/news_nlp.py:
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）を用いて -1.0〜1.0 のセンチメントスコアを算出・ai_scores テーブルへ書き込み。
    - バッチ処理（最大20銘柄/チャンク）、記事数・文字数トリム、JSON Mode のレスポンスバリデーション、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ、失敗時は個別にスキップする堅牢な実装。
    - calc_news_window により JST ベースのニュース収集ウィンドウを計算（ルックアヘッド防止のため datetime.today() を参照しない）。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321 の 200日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して market_regime テーブルへ日次判定結果を書き込む実装。
    - OpenAI 呼び出しのリトライ・エラー処理、APIキー引数／環境変数解決、フェイルセーフ（API失敗時は macro_sentiment=0.0）を備える。
    - DuckDB クエリは target_date 未満のデータのみを使用し、ルックアヘッドバイアスに配慮。
- データ処理 / ETL / カレンダー
  - src/kabusys/data/pipeline.py:
    - ETLResult dataclass を実装（取得数／保存数／品質チェック結果／エラー等を保持）。to_dict による辞書化を提供。
    - 差分更新・バックフィル・品質チェック等を想定した設計（J-Quants クライアント連携想定）。
  - src/kabusys/data/etl.py:
    - ETLResult を再エクスポート。
  - src/kabusys/data/calendar_management.py:
    - market_calendar テーブルを基にした営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合は曜日ベースのフォールバックを行う設計。
    - calendar_update_job により J-Quants からの差分取得／バックフィル／保存処理（保守的な健全性チェック付き）を実装。
    - DuckDB との互換性・NULL ハンドリングに配慮した実装。
- Research（因子計算・特徴量探索）
  - src/kabusys/research/factor_research.py:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金／出来高比率）、バリュー（PER、ROE）などの因子計算を実装。
    - DuckDB を用いた SQL と Python のハイブリッド実装。データ不足時は None を返す挙動。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算、ランク付けユーティリティ、ファクターの統計サマリーを実装。外部ライブラリに依存しない純標準ライブラリ実装。
  - src/kabusys/research/__init__.py:
    - 主要関数群と zscore_normalize の再エクスポートを追加。
- モジュール公開整理
  - src/kabusys/ai/__init__.py と research/__init__.py などで公開APIを整備。
- jquants_client 等外部クライアントの呼び出しは分離（kabusys.data.jquants_client を介して利用想定）。

Changed
- なし（初版のため変更履歴なし）。

Fixed
- なし（初版のため修正履歴なし）。

Security
- OpenAI の利用には API キー（OPENAI_API_KEY）を必須とする箇所があり、キー管理に注意する旨を明記している（Settings による環境変数取得を利用）。

Notes / Limitations
- 本リリースはライブラリ本体のデータ処理・研究・AI スコアリング等のロジック実装が中心であり、実際の取引執行ロジックや外部サービスの具体的なクレデンシャル管理・接続実装（kabuステーション API 実装や J-Quants クライアントの具体的実装など）は別モジュール（kabusys.data.jquants_client 等）に委ねられる想定です。
- DuckDB に依存するクエリを多数含むため、DuckDB 環境・スキーマ（prices_daily, raw_news, market_calendar, ai_scores, raw_financials, news_symbols, market_regime 等）が事前に整備されている必要があります。
- OpenAI 呼び出しは gpt-4o-mini を指定し JSON Mode（response_format）を利用する設計。API 仕様変更時にはエラーハンドリングやレスポンスパースの調整が必要になる可能性があります。
- ルックアヘッドバイアス防止のため、日付の扱いは外部から渡す target_date に依存する設計（内部で datetime.today()/date.today() を直接参照しない）。

Contributing
- バグ報告・改善提案は issue を立ててください。変更はセマンティックバージョニングに従って管理します。