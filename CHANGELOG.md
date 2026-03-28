CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。
バージョンは semver に従います。

Unreleased
----------
（なし）

[0.1.0] - 2026-03-28
-------------------

Added
- 初回公開リリース。日本株自動売買システム "KabuSys" のコア機能群を追加。
- パッケージ公開情報
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に設定。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 複雑な .env パース実装（export プレフィックス対応、クォート中のエスケープ処理、インラインコメント処理など）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL）と便利プロパティ（is_live / is_paper / is_dev）。
  - デフォルトの DB パス（DUCKDB_PATH, SQLITE_PATH）を明示。
- AI 関連（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメントを計算。
    - バッチ処理（最大 20 銘柄チャンク）、1 銘柄あたりの記事上限・文字数トリム、レスポンスバリデーションを実装。
    - エラー耐性: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、異常レスポンスはスキップして処理継続。
    - DuckDB 互換性考慮（executemany に空リストを渡さない等）。
    - calc_news_window ヘルパー（JST 基準のニュース時間ウィンドウ計算）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（重み 30%）を合成し、日次でレジーム判定（bull / neutral / bear）を実施。
    - マクロニュースは news_nlp の calc_news_window でウィンドウを計算、タイトル抽出後に OpenAI に送信して macro_sentiment を取得。
    - OpenAI 呼び出しに対するリトライ／フェイルセーフ（API 失敗時は macro_sentiment=0.0）。
    - レジーム判定結果を market_regime テーブルに冪等（BEGIN/DELETE/INSERT/COMMIT）で保存。
    - 日付のルックアヘッドバイアスを避ける設計（date 引数ベース、datetime.today() を参照しない）。
- データ基盤（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー管理用ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar テーブル優先の判定、未取得日は曜日ベースのフォールバック、探索上限を設定（_MAX_SEARCH_DAYS）。
    - calendar_update_job: J-Quants から差分取得して冪等保存（バックフィル・健全性チェック付き）。
  - ETL パイプライン（src/kabusys/data/pipeline.py）
    - 差分取得→保存→品質チェックのフローに対応する ETLResult データクラスを追加（src/kabusys/data/etl.py で公開）。
    - 最小データ日、バックフィルポリシー、カレンダー先読み、品質チェックの集約方法（致命的でも収集して上位で判断）を実装。
    - DuckDB テーブル存在チェック、最大日付取得ユーティリティ等を実装。
- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER / ROE）を DuckDB の prices_daily/raw_financials から計算する実装を提供。
    - データ不足時の None 処理や、営業日ベースの窓幅を取り扱う設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意ホライズン）、IC（Spearman）計算、ランク化ユーティリティ、ファクター統計サマリーを提供。
    - 外部ライブラリに依存せず標準ライブラリのみで実装（テストしやすい設計）。
- 公開 API / テスト支援
  - 多くの外部 API 呼び出し部分（OpenAI, J-Quants クライアント）を分離しており、ユニットテスト時に差し替えやすい設計（patch しやすい private 呼び出し関数を用意）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 設計上の重要点
- ルックアヘッドバイアス対策: AI スコアリングおよび各種計算はすべて target_date 引数ベースで実行し、datetime.today()/date.today() を安易に参照しないよう設計。
- フェイルセーフ: 外部 API 失敗時は例外を投げて処理全体を止めるのではなく、許容できる場合はスコア 0.0 やスキップで継続する方針を採用（ログで通知）。
- DB 書き込みの冪等性: market_regime / ai_scores 等は既存行を削除してから INSERT することで置換（部分失敗時に他コードのスコアを消さない工夫あり）。
- DuckDB 互換性: executemany に空リストを与えない等、既知のバージョン差異に配慮。
- テスト容易性: OpenAI 呼び出しやその他副作用のある関数は patch して置き換えられるように設計。

Known limitations / TODO
- jquants_client（J-Quants API 呼び出し）や kabu ステーションの実装は外部モジュールに依存しており、このリポジトリに含まれるコードはそれらクライアントの呼び出しを前提としている。
- strategy / execution / monitoring パッケージの中身は本リリースでの公開インターフェースに含まれるが、ここに含まれる具体実装は別途実装が必要（または別モジュールに存在する想定）。
- 一部の振る舞い（例: ai_scores の sentiment_score と ai_score は同値で保存される等）は将来の仕様変更で更新予定。

Breaking Changes
- なし（初回リリース）

Authors
- KabuSys 開発チーム（コード内 docstring と設計方針に基づく推定）

References
- リポジトリ内ファイルを参照: src/kabusys/config.py, src/kabusys/ai/*.py, src/kabusys/data/*.py, src/kabusys/research/*.py

（以上）