CHANGELOG
=========

すべての注記は "Keep a Changelog" の形式に準拠しています。  
このファイルはコードベース（src/kabusys 以下）の内容から推測して作成しています。

Unreleased
----------
- なし

0.1.0 - 2026-04-03
------------------

Added
- 初回公開: KabuSys 日本株自動売買システム（バージョン 0.1.0）
  - パッケージのエントリポイント: kabusys.__version__ = "0.1.0"、公開モジュール群を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定 / ロード機能（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント取り扱いに対応。
  - 同名の OS 環境変数を保護する protected 機能と override フラグを実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視 / システム関連の設定をプロパティとして公開。環境変数未設定時は明確な例外を投げる _require を実装。
  - 環境（KABUSYS_ENV）やログレベル（LOG_LEVEL）のバリデーション、is_live / is_paper / is_dev のユーティリティも提供。
  - デフォルト値や閾値の設定（CPU/MEMORY/DISK、PID/KILL フラグ等）。

- AI モジュール（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を基に銘柄毎に記事を集約し、OpenAI（gpt-4o-mini）の JSON Mode でバッチ評価。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ calc_news_window を公開。
    - バッチ処理（1回最大 20 銘柄）、1銘柄あたり記事数・文字数上限（トークン肥大対策）、リトライ（429/ネットワーク/タイムアウト/5xx）・指数バックオフ、レスポンス検証（JSON 抽出 / results 構造 / スコア数値化 / ±1.0 クリップ）を実装。
    - 書込みは部分失敗に配慮した冪等的処理（DELETE → INSERT、書き込み対象コードに限定）。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（_call_openai_api のモック化を想定）。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロ経済ニュース（LLM センチメント、重み 30%）を合成して日次レジーム（bull/neutral/bear）を算出。
    - prices_daily / raw_news の参照、ma200_ratio 計算、マクロキーワードによる記事抽出、OpenAI による JSON レスポンス検証とリトライ、スコア合成、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API エラー時はフェイルセーフで macro_sentiment=0.0 とし処理継続。
    - ルックアヘッドバイアス防止のため date の取り扱いに注意（datetime.today() を参照しない設計）。
    - _call_openai_api は news_nlp のものとは分離して実装（モジュール結合防止、テスト容易性向上）。

- データプラットフォーム（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・保存・品質チェックフローのインターフェースを実装。
    - ETLResult データクラスを提供（取得/保存件数、品質問題、エラー一覧、ユーティリティ to_dict、エラー判定プロパティ）。
    - デフォルトのバックフィル日数、最小データ日付、品質チェックの重大度判定等を定義。
    - DuckDB に対する安全なテーブル存在チェック、最大日付取得ユーティリティ等を実装（互換性と堅牢性を重視）。

  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar を利用した営業日判定ユーティリティ群（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB にデータが存在しない場合は曜日ベース（土日除外）でフォールバック。
    - next/prev/get_trading_days は DB 登録値を優先し、未登録日は曜日ベースで補完。最大探索日数で無限ループを防止。
    - nightly job: calendar_update_job により J-Quants から差分取得して冪等保存（fetch + save のラッパ）。バックフィル、健全性チェック（未来日付の異常検知）を実装。

  - ETL 公開インターフェース（kabusys.data.etl）
    - pipeline.ETLResult を再エクスポート。

  - jquants_client との連携箇所を想定（fetch / save の利用）。

- 研究 / リサーチ（kabusys.research）
  - factor_research
    - モメンタム（1M/3M/6M、MA200 乖離）、ボラティリティ（20日 ATR 等）、バリュー（PER/ROE）等の定量ファクター算出関数を実装。
    - DuckDB の SQL ウィンドウ関数を活用して効率的に算出。データ不足時は None を返す挙動。
    - 計算結果は (date, code) をキーとする dict のリストで返却。

  - feature_exploration
    - 将来リターン計算（calc_forward_returns: 任意ホライズン、入力バリデーション、単一クエリで効率取得）。
    - IC（Information Coefficient、スピアマンの ρ）計算（calc_ic: ランク相関、最小サンプル数判定）。
    - ランク変換ユーティリティ rank（同順位は平均ランク、丸め処理で ties の検出漏れを防止）。
    - factor_summary（count/mean/std/min/max/median）を提供。
    - pandas 等の外部依存は使わず、標準ライブラリと DuckDB で実装。

Changed
- 初回公開のため該当なし。

Fixed
- 初回公開のため該当なし。

Deprecated
- 初回公開のため該当なし。

Removed
- 初回公開のため該当なし。

Security
- OpenAI API キーは引数注入または環境変数 OPENAI_API_KEY により解決。未設定時は明示的に ValueError を送出して誤使用を防止。

Notes / 実装上の重要な設計思想
- ルックアヘッドバイアス防止: すべての日時ロジックは target_date 引数を基準に設計し、datetime.today()/date.today() を参照しないことを明確にしている（AI スコア算出 / レジーム算出 / ETL）。
- 冪等性: DB 書き込みは部分的に削除→挿入（DELETE → INSERT）や ON CONFLICT 相当の保存を想定しており、夜間バッチや再実行に耐える設計。
- フェイルセーフ: OpenAI 呼び出しや外部 API の失敗は全体停止とせず適切にフォールバック（スコア=0.0、処理スキップ、ログ記録）するポリシー。
- テスト容易性: OpenAI 呼び出し関数は内部関数として分離されており、unit test でモック差し替え可能。
- 外部依存: データストアとして DuckDB を利用する想定。OpenAI（gpt-4o-mini）を JSON Mode で利用する実装。

今後の想定改善点（推測）
- real-time execution / execution モジュールの詳細な実装（発注ロジック、kabuステーション連携）の追加。
- strategy・monitoring モジュールの具体的戦略実装、監視アラートの強化（LINE 通知等）。
- テストカバレッジの拡充と CI 統合。
- J-Quants クライアント周りのリトライ・レート制御の更なる堅牢化。

（以上）