CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。セマンティックバージョニングを採用しています。

[Unreleased]
-------------

- （なし）

0.1.0 - 2026-04-04
------------------

Added
- 初回リリース: kabusys パッケージを追加。
  - バージョン: 0.1.0（src/kabusys/__init__.py にて定義）

- 環境変数 / 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を追加（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは以下をサポート:
    - コメント行、先頭に "export " を付けた行
    - シングル/ダブルクォートとバックスラッシュエスケープの処理
    - クォートなし行でのインラインコメント（直前が空白/タブの '#' のみ）
  - .env 読み込みは既存 OS 環境変数を保護するため protected セットを導入し、.env.local は .env を上書き（override）可能。
  - Settings クラスを提供し、以下の設定プロパティを環境変数から取得:
    - J-Quants / kabuステーション / LINE / DB パス（DuckDB, SQLite）/ 監視用 PID/KILL フラグパス / リソース閾値（CPU/MEM/DISK）等
  - 設定値のバリデーション:
    - KABUSYS_ENV は development/paper_trading/live のいずれかでなければ ValueError
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ有効
    - 必須環境変数未設定時は ValueError（_require）

- AI モジュール (kabusys.ai)
  - news_nlp モジュール:
    - calc_news_window(target_date) により JST のニュース収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換）を計算。
    - score_news(conn, target_date, api_key=None)
      - DuckDB の raw_news / news_symbols / ai_scores を参照して銘柄ごとに記事を集約し、LLM（gpt-4o-mini）でセンチメント（-1.0～1.0）を評価して ai_scores に書き込み。
      - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり最大記事数と文字数でトリム（デフォルト: 10 件, 3000 文字）。
      - OpenAI API 呼び出しは JSON Mode を利用し、429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
      - レスポンスの堅牢なバリデーション実装（JSON 抽出、"results" リスト、コード照合、数値変換、有限性チェック）。
      - スコアは ±1.0 にクリップ。部分失敗に備え、書き込みは該当コードのみ DELETE → INSERT（トランザクション）で行い、DuckDB の executemany に空リストを渡さない安全対策を実装。
      - テスト容易性のため _call_openai_api を patch して差し替え可能。
      - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。
  - regime_detector モジュール:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - _calc_ma200_ratio により target_date 未満のデータのみを使用して MA200 乖離を算出し、データ不足時は中立（1.0）にフォールバック。
    - _fetch_macro_news でマクロキーワードに一致するタイトルを取得（最大 20 件）。
    - _score_macro で OpenAI により macro_sentiment を取得。API 失敗時は macro_sentiment=0.0 にフォールバック（例外を上げず継続）。
    - レジームスコア合成と閾値判定（BULL / BEAR の閾値）、market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）、失敗時は ROLLBACK。
    - OpenAI 呼び出しに関して news_nlp と意図的に独立した実装を採用（モジュール結合を避ける）。
    - API キーの解決は引数または環境変数 OPENAI_API_KEY。未設定時は ValueError。

- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum(conn, target_date): mom_1m/3m/6m、ma200_dev（200 日 MA に対する乖離）を計算。データ不足時は None を返す。
    - calc_volatility(conn, target_date): 20 日 ATR（true_range の平均）、相対 ATR（atr_pct）、20 日平均売買代金、出来高倍率を計算。必要な行数が不足する場合は None を返す。
    - calc_value(conn, target_date): raw_financials から直近の財務データ（report_date <= target_date）を取得し PER/ROE を計算。EPS が 0/欠損の場合は PER を None。
    - いずれも DuckDB の SQL を中心に実装し、外部 API/発注には影響を与えない設計。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=None): 翌日/翌週/翌月 等の将来リターンを一度のクエリで取得。horizons の検証（正の整数かつ <=252）を実施。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman ランク相関（IC）を実装（同順位は平均ランク）。有効レコード数が 3 未満なら None。
    - rank(values): 平均ランクを返す実装（丸めで ties の検出漏れを防止）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算するユーティリティ。
  - kabusys.data.stats の zscore_normalize を再エクスポート。

- データプラットフォーム / ETL / カレンダー (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理機能を実装（market_calendar を基に営業日判定）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にデータがない場合は曜日ベース（平日のみ営業日）でフォールバック。DB 登録がある場合は DB 値を優先。
    - calendar_update_job(conn, lookahead_days): J-Quants API から差分取得して market_calendar に冪等保存。バックフィルと健全性チェック（将来極端な last_date の検出）を実装し、例外時はログ出力して安全に 0 を返す。
  - pipeline / etl:
    - ETLResult データクラスを公開（target_date, fetched/saved counts, quality_issues, errors など）。便利メソッド: has_errors, has_quality_errors, to_dict。
    - ETL の設計方針をコード中に明記（差分更新、バックフィル、品質チェックは続行し呼び出し側で判断）。
    - _get_max_date などのユーティリティを実装（DuckDB テーブルの最大日付取得等）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- その他
  - DuckDB を主要なローカル分析 DB として利用する実装方針。
  - 多くの関数で「ルックアヘッドバイアスを避ける」ため datetime.today()/date.today() を直接参照しない設計を採用（target_date を明示パラメータとして受け取る）。
  - 主要な外部 API 呼び出し（OpenAI / J-Quants）を直接ラップし、失敗時はフェイルセーフ（スコア 0.0、ログ出力、部分書き込み保護など）で継続する設計。
  - OpenAI 呼び出し部はテスト用に差し替え可能（patch ポイントあり）。

Notes / Implementation details
- OpenAI 関連:
  - 使用モデルは gpt-4o-mini、Chat Completions API の JSON Mode（response_format={"type": "json_object"}）を使用。
  - API 呼び出しはタイムアウト 30 秒、temperature=0 固定。
  - 429/ネットワーク/タイムアウト/5xx に対して指数バックオフ（base: 1.0 秒）でリトライ。
- トランザクションと冪等性:
  - market_regime / ai_scores 等への書き込みは BEGIN/DELETE/INSERT/COMMIT のパターンで冪等性を保つ。例外発生時は ROLLBACK を試行。
  - DuckDB executemany は空リストを渡せない制約に対する保護コードあり。
- ロギング: 各処理で適切な info/debug/warning/exception ログを出力するよう実装。

Known issues / Limitations
- LINE / kabu API 等の外部実行・発注周りの機能は本バージョンのコアコードに触れているが、実際の発注フロー・外部接続の実装は含まれていない（環境設定と参照先の準備が必要）。
- AI の出力品質は LLM とプロンプト設計に依存するため、運用時はログでの監視と閾値調整が必要。
- raw_financials からの PBR・配当利回り等は現バージョンで未実装（calc_value に注記あり）。

References
- パッケージのエントリポイント: src/kabusys/__init__.py に __all__（data, strategy, execution, monitoring）を定義。README やさらなるリファレンスは今後追加予定。

--- 

（必要に応じて、リリースノートの細分化（Fixed/Changed/Deprecated/Security 等）や追加の日付・コミットハッシュを付与してください。）