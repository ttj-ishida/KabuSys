# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このプロジェクトはセマンティックバージョニングを使用します。

現在のバージョン: 0.1.0 — 2026-03-29

## [Unreleased]
（保留中の変更はありません）

## [0.1.0] - 2026-03-29
初期リリース。日本株自動売買プラットフォームのコアライブラリを提供します。主要な機能と設計上の注意点を以下にまとめます。

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報: kabusys.__init__ にバージョン "0.1.0" と主要サブパッケージの公開（data, strategy, execution, monitoring）。

- 設定 & 環境変数管理（kabusys.config）
  - .env ファイルと環境変数を読み込む自動ローダーを実装（プロジェクトルートは .git / pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーはコメント行・export プレフィックス・シングル/ダブルクォートとバックスラッシュエスケープ・インラインコメント処理等に対応。
  - _load_env_file による保護（protected）キーの概念を導入し OS 環境変数の上書きを保護。
  - Settings クラスで主要設定をプロパティとして公開（J-Quants、kabuステーション、Slack、DBパス、実行環境フラグ、ログレベル等）。値検証（KABUSYS_ENV/LOG_LEVEL の許容値チェック）を実装。
  - 必須キー未設定時には明示的なエラーを投げる _require を実装。

- AI モジュール（kabusys.ai）
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）の JSON モードで一括センチメント評価を行う score_news を実装。
    - タイムウィンドウは JST 基準（前日 15:00 ～ 当日 08:30）を UTC に変換して DB クエリに使用（calc_news_window）。
    - バッチ処理（1 API コールあたり最大 20 銘柄）、1銘柄あたり記事数/文字数上限（10記事・3000文字）によるトリム実装。
    - API の一時エラー（429、接続断、タイムアウト、5xx）に対して指数バックオフでリトライ。その他はフォールバックしてスキップ。
    - レスポンスの厳密なバリデーション実装（JSON 抽出、"results" 構造チェック、コード照合、数値チェック、スコアクリップ ±1.0）。
    - DuckDB への書き込みは冪等性を担保（取得済みコードのみ DELETE → INSERT）し、executemany の空リスト制約を回避する安全策を実装。
    - テスト用に _call_openai_api を patch 可能（ユニットテストで差し替えられる設計）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成し、日次で市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
    - prices_daily からの MA200 比率計算、raw_news からのマクロキーワード抽出、OpenAI による macro_sentiment 評価、スコア合成、market_regime テーブルへの冪等書き込みを含むフローを実装。
    - LLM 呼び出しの失敗は macro_sentiment=0.0（中立）でフェイルセーフ継続。
    - OpenAI SDK の各種例外（RateLimitError, APIConnectionError, APITimeoutError, APIError）に対するリトライ・判定ロジックを実装。
    - テスト容易性のため _call_openai_api をモジュール内で独立実装（news_nlp と共有しない設計）。

- データ基盤（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを扱うユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が不足する場合は曜日ベース（週末除外）でフォールバックする一貫性のある判定ロジック。
    - カレンダー夜間バッチ更新 job（calendar_update_job）を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック、保存呼び出し）。
    - 最大探索日数やバックフィル日数、先読み日数等の安全パラメータを導入して無限ループや過剰取得を防止。

  - ETL / パイプライン（kabusys.data.pipeline, kabusys.data.etl）
    - ETLResult データクラスを公開（target_date, fetched/saved カウント, quality_issues, errors 等）。
    - ETL パイプラインのユーティリティ関数（テーブル存在チェック、最大日付取得、market_calendar 調整ヘルパ等）を実装。
    - 差分更新、バックフィル、品質チェックを考慮した設計（品質チェックは収集して上位で判断する方式）。
    - kabusys.data.etl で pipeline.ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターン、ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得し PER / ROE を計算。
    - いずれも DuckDB の prices_daily/raw_financials のみ参照し、ルックアヘッドバイアス防止のため target_date 未満や直前データのみ参照する設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: Spearman（ランク相関）ベースの IC を実装（必要件数チェック、None/finite 判定）。
    - rank: 同順位は平均ランクにする実装（浮動小数の丸め対策を含む）。
    - factor_summary: カラム毎の count/mean/std/min/max/median を計算。
    - kabusys.research.__init__ で主要関数群を再エクスポート（zscore_normalize は kabusys.data.stats から）。

### 変更 (Changed)
- なし（本バージョンは初期公開のため、過去バージョンからの変更はありません）。

### 修正 (Fixed)
- なし（初回リリース）。

### セキュリティ (Security)
- OpenAI API キーの取り扱いは引数優先、環境変数 fallback として明示。キー未設定時は ValueError を投げることで誤使用を防止。
- .env 読み込みでファイル読み取りエラー時に警告を出力し処理継続（致命的な例外としない）。

### 設計上の注意 / 既知の挙動
- ルックアヘッドバイアス防止:
  - AI モジュールやリサーチ系の関数はいずれも datetime.today()/date.today() を直接参照しない（target_date を明示的に受け取る）。
  - DB クエリは target_date 未満 / 未満等の条件で未来データ参照を避けるよう実装。
- フェイルセーフ:
  - LLM 呼び出し失敗時はスコアを 0.0（中立）にフォールバックする箇所があるため、API 障害時でも処理継続できる設計。
- DuckDB の互換性考慮:
  - executemany に空リストを渡すと失敗するバージョンに対応するため空チェックを実装。
  - 一括更新は冪等性を保つため DELETE → INSERT の手順で行う（部分失敗時に既存データを守る）。
- テスト容易性:
  - OpenAI 呼び出し箇所は内部関数 _call_openai_api を patch 可能にしてユニットテストで模擬できる設計。

---

将来のリリースでは、Strategy / Execution / Monitoring 周りの高レベルな自動売買ロジック、より細かな品質チェックルール、外部クライアント実装（jquants_client, kabuステーションクライアント等）の公開、及びドキュメント充実を予定しています。