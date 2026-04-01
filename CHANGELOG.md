CHANGELOG
=========
この変更履歴は "Keep a Changelog" の形式に準拠しています。  
バージョニングは semver に従います。

0.1.0 - 2026-04-01
------------------

Added
- 初回リリース。kabusys パッケージの基本機能を実装・公開。
  - パッケージ情報
    - src/kabusys/__init__.py: バージョン __version__ = "0.1.0" を公開。
    - パッケージ外部公開モジュール: data, strategy, execution, monitoring を __all__ に設定（strategy/execution/monitoring は将来的な拡張を想定）。
  - 設定 / 環境変数管理
    - src/kabusys/config.py
      - .env ファイルおよび環境変数からの設定読み込み機能を実装。
      - プロジェクトルートの自動探索（.git または pyproject.toml を基準）により、カレントワーキングディレクトリに依存せずに .env を読み込む。
      - .env のパース機能を強化（export KEY= 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応）。
      - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - Settings クラスを公開し、J-Quants / kabuステーション / Slack / DB パス / 監視しきい値 / システム環境（development/paper_trading/live）等のプロパティを提供。未設定の必須変数に対しては明示的な ValueError を発生させる。
  - AI（ニュース NLP / レジーム判定）
    - src/kabusys/ai/news_nlp.py
      - raw_news と news_symbols を集約して銘柄毎のニュースを作成し、OpenAI（gpt-4o-mini）を使ったバッチセンチメント解析を実装。
      - タイムウィンドウ計算（JST基準 → DBはUTC想定）、1銘柄あたりの最大記事数・文字数トリム、最大バッチサイズ、JSON Mode での厳密なレスポンス検証を行う。
      - API リトライ（429、接続断、タイムアウト、5xx）に対して指数バックオフを実施。パース/バリデーション失敗は該当チャンクをスキップして処理を継続するフェイルセーフ実装。
      - スコアは ±1.0 にクリップし、取得成功分のみ ai_scores テーブルへ冪等的（DELETE → INSERT）に書き込む。
      - テスト容易性のため _call_openai_api 等をモック差し替え可能に設計。
      - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。
    - src/kabusys/ai/regime_detector.py
      - ETF 1321 の 200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定する機能を実装。
      - prices_daily から ma200_ratio を計算し、raw_news からマクロキーワードでフィルタしてタイトルを抽出、OpenAI で macro_sentiment を評価する（記事がない場合は LLM 呼び出しをスキップして 0.0 を使用）。
      - OpenAI 呼び出しはリトライ・エラーハンドリングを行い、最終的に market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
      - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時に 1 を返す。
      - 設計上、ルックアヘッドバイアス回避のため datetime.today()/date.today() を直接参照せず、target_date で明示的に指定する方式を採用。
  - データプラットフォーム（ETL / カレンダー管理 / パイプライン）
    - src/kabusys/data/calendar_management.py
      - JPX カレンダー管理（market_calendar テーブル）と営業日判定ユーティリティを実装。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
      - DB にカレンダー情報がない場合は土日ベースのフォールバック判定を行う。DB 値があれば DB を優先する一貫した設計。
      - calendar_update_job(conn, lookahead_days=...) により J-Quants API からの差分取得 → 保存（jquants_client 経由）を行う。バックフィル・健全性チェックを実装。
    - src/kabusys/data/pipeline.py
      - ETL の概念実装。差分取得/保存/品質チェックのワークフローに対応するユーティリティを実装。
      - ETL 実行結果を表す dataclass ETLResult を導入（target_date, fetched/saved counts, quality_issues, errors 等を保持）。
      - ETLResult.to_dict() により品質問題を辞書化して監査ログ等に使える形式で出力可能。
      - 実装は jquants_client と quality モジュールを利用する想定で、id_token 注入等テスト容易性を考慮。
    - src/kabusys/data/etl.py
      - pipeline.ETLResult を再エクスポート（公開インターフェース）。
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py
      - モメンタム（1m/3m/6m リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）を DuckDB 上の SQL と Python を組み合わせて計算する関数を実装。
      - データ不足時には None を返すなど堅牢な結果を返す仕様。
      - 公開関数: calc_momentum, calc_volatility, calc_value（いずれも conn, target_date を引数）。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns）、IC（スピアマン順位相関）計算（calc_ic）、ランキングユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
      - pandas 等の外部依存を用いず、純標準ライブラリ＋DuckDBで動作する設計。
    - src/kabusys/research/__init__.py による主要関数の再エクスポート。
  - その他
    - DuckDB を前提とした SQL クエリと処理ロジックを広範に実装（prices_daily、raw_news、ai_scores、market_regime、market_calendar 等のテーブル操作）。
    - 多くの箇所で「冪等書き込み」「部分失敗時に他データを保護する」実装方針を採用（DELETE→INSERT、対象コード絞り込み等）。
    - OpenAI クライアント呼び出し箇所はテスト時に差し替え可能な設計（モック可能）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / Known limitations
- OpenAI API キーは score_news / score_regime の引数で注入可能。None の場合は環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError を送出します。
- OpenAI 呼び出し失敗時は多くの箇所でフェイルセーフ的に 0.0 や空スコアで継続する設計になっています（可用性優先）。必要に応じて呼び出し元での再評価を推奨します。
- DuckDB の executemany に対する互換性問題（バージョン依存）を考慮して、空リストは明示的に回避する分岐を実装しています。
- calendar_update_job は内部で jquants_client を呼び出します（jquants_client 実装は別途）。market_calendar が未取得の場合は曜日ベースのフォールバックを行います。
- 一部の公開モジュール（strategy, execution, monitoring）は __all__ に含まれますが、このリリースでの実装範囲は上記データ/AI/研究/ETL に重点を置いています。

Migration
- なし（初回リリース）。

Acknowledgements / Design decisions
- ルックアヘッドバイアスを避けるため、内部実装では date/datetime の "now" を暗黙参照せず、必ず target_date を受け取る設計にしています。
- 外部 API 呼び出し（OpenAI / J-Quants）についてはリトライ/バックオフやレスポンス検証を重視し、部分失敗時に他データへ影響を最小限にする堅牢性を重視しています。

-- END --