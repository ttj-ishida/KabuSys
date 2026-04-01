Keep a Changelog に準拠した CHANGELOG.md（日本語）
（コードベースの内容から推測して作成しています）

すべての変更は semver に従います。以下は初回公開相当のリリースノートです。

[Unreleased]
- 今後の変更点やマイナー修正をここに記載します。

[0.1.0] - 2026-04-01
Added
- パッケージ基盤
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring を __all__ でエクスポート。
  - バージョン番号を "0.1.0" として確定。

- 設定/環境変数管理 (kabusys.config)
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは .git または pyproject.toml を基準に自動探索（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサーは以下に対応:
    - 空行・コメント行、先頭に export を含む行、クォート付き値のバックスラッシュエスケープ、行内コメント（クォートなしの '#' は直前が空白/タブの場合にコメントと認識）。
  - Settings クラスを提供し、主要な設定値をプロパティ経由で取得可能:
    - J-Quants / kabu ステーション / Slack / DB パス（duckdb/sqlite）/監視設定（PID, CPU/MEM/DISK閾値）/実行環境 (development/paper_trading/live)/ログレベル など。
    - 必須環境変数が未設定の場合は ValueError を発生させる _require() を用意。
    - env / log_level 値の妥当性チェックを実装。

- AI モジュール (kabusys.ai)
  - ニュース NLP スコアリング (kabusys.ai.news_nlp)
    - raw_news と news_symbols を元に銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini, JSON Mode）で -1.0〜1.0 のセンチメントスコアを算出。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（内部は UTC naive datetime で扱う）。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/回）、1銘柄あたり記事数上限・文字数トリムを実装。
    - リトライ/バックオフ戦略: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
    - レスポンス検証（JSON 抽出、results キー、型チェック、未知コード無視、数値検証）とスコアのクリップを実装。
    - スコアは ai_scores テーブルへ冪等的に（DELETE → INSERT）書き込み。部分失敗時に既存スコアを保護する設計。
    - テスト用に OpenAI 呼び出しを差し替え可能な設計（_call_openai_api の patch を想定）。
    - 公開関数: score_news(conn, target_date, api_key=None)

  - 市場レジーム判定 (kabusys.ai.regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組み合わせて日次で市場レジーム（bull/neutral/bear）を判定。
    - prices_daily から ma200_ratio を算出（target_date 未満のデータのみ使用、ルックアヘッド回避）。
    - raw_news からマクロ系キーワードでフィルタしたタイトルを抽出し、OpenAI（gpt-4o-mini）で macro_sentiment を評価（記事なしは LLM 呼び出しをスキップし 0.0 を使用）。
    - API 呼び出しでのリトライ処理、エラー時のフェイルセーフ（macro_sentiment=0.0）、およびレスポンス JSON パースの堅牢化を実装。
    - market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実施。
    - 公開関数: score_regime(conn, target_date, api_key=None)

- Data / ETL / カレンダー関連 (kabusys.data)
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを使った営業日判定ロジックを提供:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にデータがある場合は DB 値を優先、未登録日は曜日（週末）ベースでフォールバックする一貫した挙動。
    - 夜間バッチ更新 job (calendar_update_job) を実装。J-Quants API から差分取得して market_calendar を idempotent に更新（バックフィルと健全性チェックを含む）。
  - ETL パイプライン (kabusys.data.pipeline / kabusys.data.etl)
    - ETLResult データクラスを導入し、ETL 実行結果（取得数・保存数・品質チェック結果・エラー）を集約。
    - 差分取得、保存（jquants_client の save_* を想定）、品質チェックのフロー設計を備えた下地を実装。
    - kabusys.data.etl で ETLResult を再エクスポート。
  - 内部ユーティリティ: テーブル存在チェック、最大日付取得などの補助関数を実装（pipeline 内）。

- Research / ファクター (kabusys.research)
  - factor_research: モメンタム / ボラティリティ / バリュー系ファクターを実装:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率（データ不足は None）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS=0/欠損時は None）。
  - feature_exploration: 将来リターン計算 / IC（スピアマン） / 統計サマリー / ランク（同順位平均ランク）の実装:
    - calc_forward_returns: デフォルト horizons [1,5,21]、入力バリデーションあり。
    - calc_ic: factor と forward return を code で結合して Spearman の ρ を算出（有効レコード < 3 の場合は None）。
    - factor_summary: count/mean/std/min/max/median を計算。
    - rank: 同順位の平均ランク、丸めによる ties 対応を実装。
  - research パッケージで主要関数を再エクスポート。

Changed
- （初回リリースのため該当なし）

Fixed / Behavior
- 全体設計でルックアヘッドバイアス回避を徹底:
  - datetime.today()/date.today() に依存せず、score 系関数は target_date を明示的に受け取る。
  - DB クエリは target_date 未満／間隔指定などで未来データを参照しないよう実装。
- 外部 API 呼び出しに対する堅牢性を強化:
  - OpenAI API 呼び出しのリトライ（429/ネットワーク/5xx）、API レスポンスの検証とフォールバック（例: 0.0）を行い、例外で全処理が停止しない設計。
- DB 書き込みは冪等操作（DELETE → INSERT、ON CONFLICT 想定）を用いて部分失敗時に他データを保護する設計。

Security
- OpenAI や Slack、kabu API、J-Quants の認証情報は環境変数経由で必須に設定（Settings で必須項目をチェック）。
- .env 自動読込は意図的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Known issues
- pipeline._get_max_date の末尾が不完全（ソース中に "return date.fro" のような途中の記述があり、未完/タイポの可能性があります）。この関数の戻り値ロジックは実装補完が必要です。
- jquants_client（kabusys.data.jquants_client）はこの差分の中で参照されているが、実装は別モジュールに依存します。実動作には jquants_client の実装が必要です。
- データベーススキーマ（prices_daily, raw_news, ai_scores, market_regime, market_calendar, raw_financials, news_symbols など）は別途用意する必要があります。
- OpenAI SDK の利用は v1 系に依存する呼び出し形態を想定しており、将来の SDK 変更に対しては適宜対応が必要。
- strategy / execution / monitoring モジュールの公開は __all__ に含まれるが、本差分ではこれらの実装は未提示（または別ファイルに存在する想定）。

開発者向け補足
- テスト容易性のため、OpenAI 呼び出し（各モジュール内の _call_openai_api）は unittest.mock.patch により差し替え可能にしている。
- DuckDB をメインに利用する設計であり、executemany に空リストを投げるとエラーとなる点（DuckDB 0.10 の制約）に対するガードをコード内で行っている。

---

この CHANGELOG はコードの現状から読み取れる意図・仕様を基に作成しています。実際のリリースノートとして利用する際は、本番での動作確認や未実装/依存部の実装状況に合わせて調整してください。