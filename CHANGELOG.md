# CHANGELOG

すべての注目すべき変更点を記載します。本ドキュメントは Keep a Changelog の形式に準拠しています。

## [0.1.0] - 2026-03-28

### 追加 (Added)
- 初回公開: KabuSys 日本株自動売買システムのコアライブラリを追加。
- パッケージエントリポイント
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` に設定。
  - `__all__` に主要サブパッケージをエクスポート（data, strategy, execution, monitoring）。
- 設定管理 (`kabusys.config`)
  - .env ファイルまたは環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出ロジックを追加（.git または pyproject.toml を基準。CWD に依存しない）。
  - .env パース器を実装（コメントや export 形式、クォート中のエスケープ対応、インラインコメント処理）。
  - 自動環境変数ロードの優先順位: OS 環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - 必須環境変数取得ヘルパ (`_require`) と Settings クラスを提供。
  - Settings で以下のプロパティを提供:
    - J-Quants / kabuステーション / Slack / DBパス（DuckDB/SQLite） / 環境種別（development, paper_trading, live）/ ログレベル（DEBUG, INFO, ...）/ is_live/is_paper/is_dev 判定。
  - 環境値のバリデーション（無効な KABUSYS_ENV / LOG_LEVEL は ValueError）。

- AI ニュース分析 (`kabusys.ai`)
  - news_nlp モジュール
    - raw_news / news_symbols を対象に、指定ウィンドウ（前日15:00 JST〜当日08:30 JST）で記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄別センチメントを算出。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり記事数・文字数上限（既定: 10 件 / 3000 文字）、JSON Mode 応答のバリデーションとトリミング。
    - 再試行ポリシー: 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。
    - レスポンス検証で未知コード無視、スコアを ±1.0 にクリップ。
    - 書き込みは冪等的に実施（DELETE → INSERT、DuckDB executemany の互換性考慮）。
    - テスト用に `_call_openai_api` を patch 可能（モジュール固有の差し替えポイント）。
  - regime_detector モジュール
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - MA 計算でルックアヘッドを防ぐため target_date 未満のデータのみを使用。データ不足時は中立扱い。
    - マクロニュース抽出はマクロキーワードリストに基づき raw_news からタイトルを取得。記事がない場合は LLM 呼び出しをスキップして 0.0 を使用。
    - OpenAI 呼び出し・リトライ・フォールバック（失敗時 macro_sentiment=0.0）を実装。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB 書き込み失敗時はロールバックし例外を伝播。

- 研究（Research）モジュール (`kabusys.research`)
  - factor_research
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離を計算する `calc_momentum`。
    - ボラティリティ/流動性: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比を計算する `calc_volatility`。
    - バリュー: raw_financials を用いた PER / ROE 計算を行う `calc_value`。
    - SQL（DuckDB）ベースでの実装。出力は (date, code) ベースの dict リスト。
  - feature_exploration
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン、デフォルト [1,5,21]）。
    - IC（スピアマンの ρ）計算 `calc_ic`（rank を内部実装）。
    - ランキング補助 `rank`（同順位は平均ランク）。
    - 統計サマリー `factor_summary`（count/mean/std/min/max/median）。
    - pandas 等の外部依存なしで純粋 Python + DuckDB の実装。

- データプラットフォーム（Data）モジュール (`kabusys.data`)
  - calendar_management
    - JPX マーケットカレンダー管理、営業日判定関数群を実装:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーが無い場合は曜日ベースのフォールバック（平日を営業日）を使用。
    - カレンダー更新バッチ `calendar_update_job`（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック）。
    - 最大探索範囲やバックフィル日数等の安全機構を実装。
  - pipeline / etl
    - ETLResult データクラスを公開（取得件数、保存件数、品質問題、エラー一覧、has_errors 等）。
    - ETL パイプライン設計に基づく差分取得・保存・品質チェックの土台を実装（jquants_client / quality モジュールとの連携を想定）。
  - jquants_client を使った差分取得・保存ロジックの説明に準拠した実装（実際のクライアントは別モジュールで提供）。

### 変更 (Changed)
- N/A（初回リリースのため該当なし）。

### 修正 (Fixed)
- N/A（初回リリースのため該当なし）。

### 既知の注意点 / 設計上の重要点 (Notes)
- ルックアヘッドバイアス防止: 主要な関数（news/regs/research/etc）は internal に date 引数を受け取り、datetime.today()/date.today() を直接参照しないよう設計されています。
- OpenAI API の取り扱い:
  - 環境変数 `OPENAI_API_KEY` または各関数の api_key 引数でキーを注入可能。
  - 各 AI モジュールは JSON mode を利用し、レスポンスの堅牢な検証とフェイルセーフ（失敗時は 0.0 またはスキップ）を行います。
  - テスト容易性のため `_call_openai_api` を patch して呼び出しを模擬できます（モジュール毎に独立した実装）。
- DuckDB 関連:
  - 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で実施し、冪等性を保つため DELETE→INSERT のパターンを多用。
  - DuckDB executemany の空リスト制約等の互換性考慮が含まれます（空パラメータ時は条件分岐で回避）。
- 環境変数の自動読み込み:
  - パッケージインポート時に自動で .env/.env.local をプロジェクトルートから読み込む処理が走ります（無効化可）。
  - OS 環境変数はデフォルトで保護（.env による上書き回避）。

### セキュリティ (Security)
- 機密情報（API キー・パスワード等）は環境変数で扱う前提。README/.env.example に従って設定してください（.env の読み込みはローカルファイルに限定）。

---

今後のリリースでは、strategy / execution / monitoring サブパッケージの具体的な売買ロジックやオーダー実行部分、さらにユニットテスト・統合テスト、CI/リリース手順を追記する予定です。