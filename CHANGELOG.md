KEEP A CHANGELOG — kabusys

すべての変更は "Keep a Changelog" の形式に従って記載しています。  
初回リリースの内容はソースコードから推測してまとめています。

Unreleased
----------
- （なし）

[0.1.0] - 2026-04-01
--------------------
Added
- パッケージ初版を追加。
  - パッケージメタ:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - エクスポート: data, strategy, execution, monitoring（将来的な拡張向けの名称空間）
- 環境設定管理 (src/kabusys/config.py)
  - .env および .env.local の自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - 複雑な .env パースを実装:
    - コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - override / protected オプション付きでファイル読み込み。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 必須環境変数取得ヘルパー _require と Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などのプロパティを公開
    - DUCKDB_PATH / SQLITE_PATH 等のデフォルトパス、監視閾値（CPU、メモリ、ディスク）と PID ファイルパスを設定
    - KABUSYS_ENV 値検証（development / paper_trading / live）および LOG_LEVEL 検証
    - is_live / is_paper / is_dev のユーティリティプロパティ

- AI モジュール (src/kabusys/ai)
  - ニュースセンチメント分析 (news_nlp.py)
    - raw_news / news_symbols を集約し、銘柄毎にニュースを結合して OpenAI (gpt-4o-mini) に送信、JSON モードで結果を受け取り ai_scores テーブルへ書き込み。
    - バッチ処理（最大20銘柄／チャンク）、1銘柄あたりの記事/文字数上限、JSON レスポンスのバリデーション実装。
    - 429/ネットワーク断/タイムアウト/5xx に対するエクスポネンシャルバックオフとリトライ。
    - 部分失敗時の保護（取得済みコードのみ DELETE→INSERT）と DuckDB executemany の空リスト制約への対策。
    - テスト容易性のため OpenAI 呼び出し部分は差し替え可能（_call_openai_api を patch 可能）。
    - 関数公開: score_news(conn, target_date, api_key=None)
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM 評価（重み 30%）を合成して日次で market_regime テーブルへ書き込み。
    - マクロ記事フィルタリング用キーワードリスト、最大記事数、OpenAI 呼び出しのリトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - ルックアヘッドバイアス防止のため target_date 未満のデータのみを使用し、datetime.today() を直接参照しない設計。
    - 関数公開: score_regime(conn, target_date, api_key=None)

- Data モジュール (src/kabusys/data)
  - マーケットカレンダー管理 (calendar_management.py)
    - market_calendar テーブルを用いた営業日判定・次/前営業日取得・期間内営業日列挙・SQ判定機能を実装。
    - DB データが無い／未登録日の場合は曜日ベース（平日を営業日）でフォールバックする一貫したロジック。
    - calendar_update_job により J-Quants から差分取得→冪等保存（バックフィル・健全性チェックを含む）を実装。
  - ETL パイプライン（pipeline.py / etl.py）
    - 差分取得・idempotent 保存（jquants_client 経由）・品質チェック（quality モジュール連携）を行う ETLResult データクラスを実装。
    - ETLResult には取得件数／保存件数／品質問題／エラーの集約と辞書化ユーティリティを提供。
    - _get_max_date / _table_exists 等の DB ヘルパーも実装されている（パイプラインの内部ロジックに利用）。

- Research モジュール (src/kabusys/research)
  - ファクター計算 (factor_research.py)
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR 等）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials から計算する関数を提供。
    - 欠損・データ不足時の None の取り扱い、営業日バッファなど設計上の配慮あり。
    - 関数公開: calc_momentum, calc_volatility, calc_value
  - 特徴量探索 (feature_exploration.py)
    - 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）の計算、ファクター統計サマリー、ランク変換ユーティリティを実装。
    - pandas 等非依存で純粋 Python / SQL 実装。
    - 関数公開: calc_forward_returns, calc_ic, factor_summary, rank
  - re-export: zscore_normalize を kabusys.data.stats から再エクスポート

Changed
- （初版のため変更履歴なし）

Fixed
- （初版のため修正履歴なし）

Notes / Implementation details / 制約
- オフライン設計:
  - 日付周りの処理はすべて target_date ベースで行い、datetime.today() や date.today() を直接参照しない設計。バックテストや研究用途でのルックアヘッドバイアスを防止。
- OpenAI 関連:
  - gpt-4o-mini を想定。JSON mode を用いた厳格なレスポンスを期待するが、レスポンスに余計な前後テキストが混入した場合の復元ロジックあり。
  - API 呼び出しで失敗した場合はロギングしてフェイルセーフ（0.0 を使用／該当チャンクをスキップ）で継続。
  - テスト用に _call_openai_api をモック可能にしている。
- DuckDB / SQL の互換性対策:
  - executemany に空リストを渡すと失敗するバージョン（例: DuckDB 0.10）への対応を実装。
  - idempotent 書き込み（DELETE→INSERT や ON CONFLICT 相当の処理）により一貫性を保持。
- 必須外部設定:
  - OpenAI API キー (OPENAI_API_KEY または関数引数)、J-Quants リフレッシュトークン (JQUANTS_REFRESH_TOKEN)、kabuステーションのパスワード (KABU_API_PASSWORD)、Slack トークン/チャンネルなどの設定が必要。
- テスト / 拡張性:
  - 各所にモック・差し替えポイントを設けており、ユニットテストの容易化を意図。
  - モジュール結合を下げるため、news_nlp と regime_detector は OpenAI 呼び出しの内部実装を共有しない設計。

今後の予定（推測）
- strategy / execution / monitoring の具体実装（発注・監視・運用ロジック）の追加。
- データ品質チェック（quality モジュール）の詳細実装・監査ログ強化。
- ドキュメント（README / API usage）の充実と CLI / バッチ運用スクリプトの提供。

---

参考（環境変数の主なキー）
- OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL

（この CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際の変更履歴やリリースノートは開発履歴に基づいて調整してください。）