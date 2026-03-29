CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット方針
- 変更は利用者（開発者）に分かりやすい粒度で記載しています。
- 「Added / Changed / Fixed / Security」カテゴリを用います。

0.1.0 - 2026-03-29
-----------------

初回リリース。日本株自動売買システム "KabuSys" の基盤機能を実装・公開しました。
主な特徴はデータETL、マーケットカレンダー管理、因子（ファクター）計算、ニュースの NLP スコアリング、LLM を用いた市場レジーム判定、環境設定ユーティリティなどの統合です。

Added
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージ名、バージョン（0.1.0）、主要サブパッケージの公開（data, strategy, execution, monitoring）。

- 環境設定・自動 .env ロード
  - src/kabusys/config.py:
    - .env/.env.local 自動読み込み機能（プロジェクトルート判定は .git または pyproject.toml ベース）。
    - export KEY=val 形式、クォート／エスケープ処理、行内コメント扱いなどに対応するパーサ実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / データベースパス / 実行環境（development/paper_trading/live）/ログレベルを環境変数から取得。
    - 必須環境変数未設定時の明確なエラー (ValueError)。

- AI 関連モジュール（OpenAI を利用）
  - src/kabusys/ai/news_nlp.py:
    - raw_news と news_symbols をもとにニュースを銘柄別に集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込む。
    - タイムウィンドウ設定（JST 前日15:00〜当日08:30 → UTC 変換）とチャンクバッチ処理（最大20銘柄 / バッチ）。
    - 1銘柄あたり記事数上限・文字数トリム（デフォルト：最大10記事・3000文字）。
    - JSON Mode を用いたレスポンス検証（パース回復処理含む）、スコア ±1.0 クリッピング。
    - エラー（429/ネットワーク断/タイムアウト/5xx）は指数バックオフでリトライ、失敗時はスキップして継続（フェイルセーフ）。
    - DuckDB の executemany の制約対応（空パラメータ回避）。
    - パブリック API: score_news(conn, target_date, api_key=None)。

  - src/kabusys/ai/regime_detector.py:
    - ETF 1321（日経225連動型）の200日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次市場レジーム（bull / neutral / bear）を判定。
    - マクロニュース抽出（キーワードリスト）→ OpenAI（gpt-4o-mini、JSON出力）で macro_sentiment を算出。
    - LLM 呼び出しのリトライ・フェイルセーフ実装（API 失敗時は macro_sentiment=0.0）。
    - 判定結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時の ROLLBACK 処理）。
    - パブリック API: score_regime(conn, target_date, api_key=None)。

- データ関連ユーティリティ
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダー管理（market_calendar）: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day などの営業日ロジックを提供。
    - DB 登録値を優先しつつ、登録がない日付は曜日ベースでフォールバック（週末は非営業日）。
    - next/prev_trading_day は最大探索日数制限（_MAX_SEARCH_DAYS）を設けて安全装置。
    - calendar_update_job により J-Quants から差分取得 → 冪等保存、バックフィル・健全性チェックを実装。
    - フォールバックの明文化（market_calendar が未取得の場合の振る舞い）。

  - src/kabusys/data/pipeline.py / src/kabusys/data/etl.py:
    - ETL パイプラインの骨組み、差分更新・保存・品質チェック設計に基づく実装。
    - ETLResult データクラス（target_date / fetched/saved counts / quality_issues / errors）を実装し、to_dict() によるシリアライズを提供。
    - 最小データ開始日・カレンダー先読み・デフォルトバックフィル日などの定数を定義。

  - src/kabusys/data/__init__.py:
    - ETLResult の公開を含むデータモジュールの初期化（etl で再エクスポート）。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py:
    - Momentum, Volatility, Value, Liquidity 等の定量ファクター計算を実装。
    - SQL を活用した DuckDB ベースの高速処理。出力は (date, code) をキーとする辞書リスト。
    - ma200_dev や各種モメンタム（1/3/6ヶ月）、ATR20、平均売買代金、出来高比率、PER/ROE の算出など。

  - src/kabusys/research/feature_exploration.py:
    - 将来リターン（forward returns）計算、IC（Spearman ランク相関）計算、ランク付けユーティリティ、ファクター統計サマリーを実装。
    - pandas 等に依存せず純標準ライブラリで完結。
    - rank() は同順位に平均ランクを与える実装（丸めで ties 判定の安定化）。

  - src/kabusys/research/__init__.py:
    - 上記関数群のエクスポートを整備。

- ログ・例外処理・設計方針の明示
  - 主要モジュールで logging を利用し、情報・警告・例外を詳細に記録。
  - ルックアヘッドバイアス回避のため、datetime.today() / date.today() を直接参照しない設計（score_news/score_regime 等は target_date を必須パラメータにする）。
  - DuckDB を一貫して利用する設計（データ操作は SQL を主体）。

Changed
- 初回リリースのため「Changed」はなし。

Fixed
- 初回リリースのため「Fixed」はなし。
  - ただし、フェイルセーフやパース回復（JSON の前後余計テキスト抽出等）など、堅牢性向上の実装を多数含む。

Security
- OpenAI API キーは明示的に必要
  - score_news / score_regime は api_key 引数または環境変数 OPENAI_API_KEY が未設定の場合 ValueError を送出する設計。
- 環境変数ロード時に OS 環境（既存キー）を protected として上書きを防止する仕組みを実装。

Public API の抜粋（主要関数／クラス）
- settings: Settings インスタンス（kabusys.config）
- score_news(conn, target_date, api_key=None) (kabusys.ai.news_nlp)
- score_regime(conn, target_date, api_key=None) (kabusys.ai.regime_detector)
- calc_momentum / calc_value / calc_volatility (kabusys.research.factor_research)
- calc_forward_returns / calc_ic / factor_summary / rank (kabusys.research.feature_exploration)
- is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job (kabusys.data.calendar_management)
- ETLResult (kabusys.data.pipeline / kabusys.data.etl)

Notes / 既知の設計意図（利用前に留意）
- API 呼び出し（OpenAI / J-Quants）失敗時は「継続かつ部分的スキップ」を基本ポリシーとする（完全停止ではない）。
- DuckDB executemany の実装差異に配慮して空リストの executemany 呼び出しを回避している。
- 日付・時間は明確に date / UTC naive datetime を使い、タイムゾーン混在を避ける方針。
- 一部定数（バッチサイズ／ウィンドウ設定／重み／閾値 等）はモジュール内定数で定義されており、将来的なチューニングが可能。

今後の予定（示唆）
- strategy / execution / monitoring サブパッケージの実装拡張（初期版ではエントリポイントのみ公開）。
- ai モジュールの堅牢化（モデル選択やリトライ戦略の細分化）、品質チェックの出力活用。
- ETL パイプラインの統合テストと運用向け監視・アラート機構の追加。

ライセンス、貢献方法、サポート方法などは別ドキュメント（README / CONTRIBUTING）を参照してください。