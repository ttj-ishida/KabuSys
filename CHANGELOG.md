# CHANGELOG

この CHANGELOG は "Keep a Changelog" のフォーマットに従い、日本語で記載しています。

全般的な方針：
- リリースは semantic versioning に従います。
- 各項目はコード内の実装・設計コメントから推測して記載しています。

## [Unreleased]
- （現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-28
初回公開リリース

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys。トップレベルで data, strategy, execution, monitoring を公開する設計を追加。
  - バージョン情報: __version__ = "0.1.0" を追加。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルと環境変数の自動読み込み機能を実装。
    - プロジェクトルート判定は .git または pyproject.toml を基準として行い、CWD に依存しない探索を実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - OS 環境変数（既存の os.environ）を保護する protected 機能を備え、override オプションにより上書き制御が可能。
  - .env パーサーは以下の形式をサポート:
    - コメント行（#）と export KEY=val 形式
    - シングル/ダブルクォートおよびバックスラッシュエスケープの処理
    - クォートなし値に対するインラインコメント処理（'#' の直前が空白またはタブの場合にコメント扱い）
  - Settings クラスを提供:
    - J-Quants / kabuステーション / Slack / DB パス 等のプロパティを環境変数から取得（必須値は _require で検証し未設定時に ValueError を投げる）。
    - 環境モードチェック（development / paper_trading / live）とログレベル検証（DEBUG..CRITICAL）を実装。
    - duckdb/sqlite のデフォルトパスを設定。

- AI モジュール（kabusys.ai）
  - ニュースセンチメント / レジーム検出機能を実装。
  - 共通:
    - OpenAI（gpt-4o-mini）を JSON Mode で利用する実装（client.chat.completions.create を使用）。
    - テストで差し替え可能な _call_openai_api フック（unittest.mock.patch を想定）。
    - 429 / ネットワーク切断 / タイムアウト / 5xx に対する指数バックオフ付きリトライ実装。
    - API 失敗時はフェイルセーフによりスコア 0.0 を使用し、処理を継続する設計。
  - news_nlp.score_news:
    - ニュースのタイムウィンドウを JST 基準で定義（前日 15:00 JST ～ 当日 08:30 JST に相当する UTC 範囲を計算）。
    - raw_news + news_symbols を使い、銘柄ごとに記事を集約（1 銘柄あたり最新記事上限・文字数トリムあり）。
    - 最大 20 銘柄 / チャンクでバッチ送信し、API レスポンスを検証して ai_scores テーブルへ冪等的に書き込み（DELETE → INSERT）。
    - レスポンスのバリデーション (results キー, code と score の存在・型チェック、スコアの有限性チェック) を実装。
    - スコアは ±1.0 にクリップ。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定。
    - prices_daily から target_date 未満のデータのみを参照してルックアヘッドを防止。
    - マクロ記事が存在しない場合や API が失敗した場合は macro_sentiment=0.0 として処理。
    - 計算結果は market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時はロールバック処理を行う。

- データプラットフォーム / ETL（kabusys.data）
  - calendar_management:
    - JPX カレンダー（market_calendar）管理ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar が未取得時は曜日ベースのフォールバック（平日を営業日）を行う一貫した挙動を実装。
    - 夜間バッチ更新 job (calendar_update_job) を実装し、J-Quants クライアント経由で差分取得・保存（バックフィルと健全性チェックを含む）。
  - pipeline / etl:
    - ETLResult データクラスを実装し、ETL 処理のフェッチ数 / 保存数 / 品質問題 / エラー一覧を保持。
    - ETLResult.to_dict により品質問題を (check_name, severity, message) の辞書一覧として出力可能。
    - データの差分更新、バックフィル、品質チェック（quality モジュール連携）を想定した設計。
    - data.etl は ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン・200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）等のファクター計算を実装。
    - DuckDB の SQL を用いた実装で、prices_daily / raw_financials テーブルのみを参照することで生産環境の取引や外部 API 呼び出しを行わない安全な実装。
    - データ不足時は None を返す等の堅牢な挙動。
  - feature_exploration:
    - 将来リターン計算 (calc_forward_returns)、IC（Spearman の ρ）計算 (calc_ic)、ランク付けユーティリティ (rank)、ファクター統計サマリー (factor_summary) を実装。
    - pandas 等に依存しない標準ライブラリベースの実装。
    - calc_forward_returns は複数ホライズンを一度のクエリで取得する設計（ホライズン検証とスキャン範囲の制限あり）。

### 変更 (Changed)
- 初回リリースのため、過去リリースからの変更はありません。

### 修正 (Fixed)
- 初回リリースのため、過去リリースからの修正はありません。

### 注意事項 / 実装上の制約
- OpenAI API の利用には OPENAI_API_KEY が必要。api_key 引数を明示的に渡すことも可能。
- news_nlp の出力仕様では「必ず提示した銘柄コードのみを返す」等のプロンプト制約を利用しているが、LLM の挙動に依存するためレスポンスは厳密に検証する実装を行っている（検証失敗時は該当チャンクをスキップ）。
- DuckDB に対する executemany の空リストバインド制約（DuckDB 0.10 系）を考慮したコードを書いており、空の場合は実行をスキップする。
- 一部設計メモとして PBR・配当利回りは現バージョンで未実装（calc_value の注釈）。
- 日付処理はルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない関数設計が多く採用されている（ただし calendar_update_job など一部は実行時の今日を参照）。

### セキュリティ (Security)
- 環境変数読み込みで OS 環境を保護する仕組み（protected set）を提供。重要な値は .env を用いて管理するよう注意喚起。

---

この CHANGELOG はコード内のドキュメント文字列／実装からの推測に基づくため、実際のリリースノートとは差分がある可能性があります。必要があれば特定モジュールごとに詳細なリリースノートを作成します。