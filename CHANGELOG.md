# Changelog

すべての重要な変更をここに記載します。フォーマットは「Keep a Changelog」のガイドラインに準拠しています。

注: この CHANGELOG はリポジトリ内の現在のコードベースから機能・設計意図を推測して作成しています（実装差分履歴ではなく初期リリース相当のまとめとして記載しています）。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-31

初期リリース。日本株のデータ取得・ETL、ファクター計算、ニュースNLP・市場レジーム判定、カレンダー管理、設定管理など、コア機能を提供します。

### 追加
- パッケージ基礎
  - kabusys パッケージ初期エントリ（src/kabusys/__init__.py）。公開サブパッケージ: data, strategy, execution, monitoring。
  - パッケージバージョン設定: __version__ = "0.1.0"。

- 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルートの検出は .git または pyproject.toml を基準とする）。
  - 優先順位: OS 環境変数 > .env.local > .env。テスト等で自動ロードを無効にするための KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パーサー追加:
    - コメント行 / 空行 / export KEY=val 形式に対応。
    - シングル/ダブルクォート内でのバックスラッシュエスケープ処理に対応。
    - クォートなしの場合に inline コメント（#）の扱いを適切に処理。
  - 環境変数取得ユーティリティ Settings クラスを追加（J-Quants、kabuAPI、Slack、DB パス、監視閾値、実行環境などをプロパティとして提供）。
  - 必須変数未設定時は明示的に ValueError を発生させる（例: OPENAI_API_KEY を使用する機能はキー未設定で ValueError）。

- AI（ニュース / レジーム判定）（src/kabusys/ai）
  - news_nlp モジュール（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols から記事を集約して OpenAI（gpt-4o-mini）に送信し、銘柄ごとに -1.0〜1.0 のセンチメントスコアを算出して ai_scores テーブルへ書き込む処理を提供。
    - タイムウィンドウ計算（calc_news_window）: JST ベースで「前日 15:00 〜 当日 08:30」を対象（DB には UTC naive datetime で比較）。
    - バッチ処理（最大 20 銘柄/リクエスト）、1 銘柄あたりの記事数・文字数上限（トークン膨張対策）を実装。
    - API 呼び出しに対する冗長性: 429、ネットワーク断、タイムアウト、5xx を指数バックオフでリトライ。
    - OpenAI の JSON Mode 出力を前提にレスポンスを厳密に検証（results 配列、code/score の存在、数値変換、未知コードの無視、スコア ±1.0 でクリップ）。
    - 部分成功時の DB 書き換え戦略: 成功コードのみ DELETE→INSERT で置換（部分失敗で他コードの既存スコアを保護）。
    - テストフレンドリー: _call_openai_api をモック差し替え可能。
  - regime_detector モジュール（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを防止。
    - マクロキーワードで raw_news のタイトルを抽出し、OpenAI に JSON 出力で評価を依頼（gpt-4o-mini）。記事がない場合は LLM 呼び出しをスキップして macro_sentiment=0.0。
    - API 失敗時はフェイルセーフとして macro_sentiment=0.0 にフォールバック。5xx 等はリトライ（指数バックオフ）。
    - 合成スコアを -1〜1 にクリップし閾値によりラベル化（BULL/BEAR 判定閾値を定義）。
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試行して例外を伝播。
    - テスト用に OpenAI 呼び出し箇所を切り分け（モジュール間で private 関数を共有しない設計）。

- データ（src/kabusys/data）
  - calendar_management モジュール（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを利用した営業日判定ロジックを実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB にデータがない場合のフォールバックは曜日ベース（土日非営業日）。
    - 夜間バッチ用 calendar_update_job: J-Quants から差分取得して market_calendar を冪等保存。バックフィル・健全性チェックを実装。
  - ETL / pipeline（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを追加（取得件数・保存件数・品質問題・エラーの集約）。
    - 差分更新、バックフィル、品質チェック連携を想定した ETL のインターフェースを提供（jquants_client と quality モジュールを利用する前提）。
    - テスト容易性のため id_token 等の注入を想定した設計。
  - jquants_client の再利用を意図した設計や DuckDB 前提の実装。

- 研究（research）（src/kabusys/research）
  - factor_research モジュール（src/kabusys/research/factor_research.py）
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR）、流動性（20 日平均売買代金、出来高比率）、バリュー（PER, ROE）等のファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB SQL を用いて prices_daily / raw_financials を参照し、(date, code) をキーとする dict のリストを返す仕様。
    - データ不足時の扱い（必要行数未満なら None を返す）を明確化。
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、ランク変換ユーティリティ（rank）、統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で完結する実装。
  - zscore_normalize を含むデータ統計ユーティリティを re-export（src/kabusys/research/__init__.py）。

### 改善（設計上の注意点／堅牢性）
- ルックアヘッドバイアス対策: 多くの機能で datetime.today()/date.today() を直接参照せず、target_date を明示的に受け取る設計。
- DB 書き込みは冪等性・部分失敗耐性を考慮（DELETE→INSERT や個別 executemany を利用）。
- OpenAI 呼び出しは JSON Mode を使用し、レスポンス検証・パース失敗対策（前後の余計なテキストから最外の {} を抽出）を実装。
- テスト容易性: OpenAI 呼び出しや内部関数をモック差し替えしやすい設計（プライベートな _call_openai_api を明示）。
- エラー・例外の扱い: API 呼び出しでの一時的エラーは警告ログを出しフォールバック、DB 書込失敗は ROLLBACK を試行して例外を伝播。

### 破壊的変更
- なし（初期リリースのため該当なし）。

### 修正
- なし（初期リリースのため該当なし）。

### 削除
- なし（初期リリースのため該当なし）。

### セキュリティ
- 環境変数の取り扱いを慎重に行う設計（.env の自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
- OpenAI API キー等の必須機密は Settings で必須チェックを行い、未設定時に明示的なエラーを発生させる。

---

注記:
- OpenAI（gpt-4o-mini）への依存箇所は外部 API 呼び出しを伴うため、実行時には OPENAI_API_KEY の設定が必要です。キー未設定で score_news / score_regime を呼ぶと ValueError が発生します。
- DuckDB を前提とする関数群が多く含まれます。実行前に想定されるスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials 等）が整っている必要があります。
- この CHANGELOG はコード内容から推測して作成したドキュメントです。実際のリリース履歴やコミット単位の変更ログが必要な場合は git の履歴から差分を抽出してください。