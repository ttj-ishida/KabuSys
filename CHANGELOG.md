CHANGELOG
=========

すべての重要な変更点はこのファイルに記載します。  
形式は「Keep a Changelog」に準拠します。

Unreleased
----------

（なし）

0.1.0 - 2026-04-03
------------------

Added
- パッケージ初回公開相当の機能群を追加。
  - kabusys パッケージのエントリポイントを追加（__version__ = 0.1.0）。
- 環境設定／読み込み機能（kabusys.config）を追加。
  - .env/.env.local ファイルをプロジェクトルート（.git または pyproject.toml を起点）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - export KEY=val、シングル／ダブルクォート、インラインコメント等を考慮した .env パーサ実装。
  - 既存 OS 環境変数を保護する protected オプション、override 動作の制御。
  - 必須環境変数取得時に見つからない場合は ValueError を送出する _require ユーティリティ。
  - J-Quants、kabuステーション、LINE API、DBパス、監視用ファイルパス、閾値、実行環境（development/paper_trading/live）等の設定プロパティを提供。
  - デフォルト値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH 等）を設定。

- ニュースNLP モジュール（kabusys.ai.news_nlp）を追加。
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を取得。
  - バッチング（最大20銘柄／チャンク）、1銘柄あたり最大記事数・最大文字数（トリム）を実装。
  - OpenAI 呼び出し失敗（429, ネットワーク, タイムアウト, 5xx）に対する指数バックオフリトライ。
  - JSON モードのレスポンス検証ロジック（余分な前後テキスト削除や results リストの構造検証）、スコア数値化・±1.0 クリップ。
  - 部分失敗に備え、ai_scores への書き込みは対象コードのみを DELETE → INSERT で上書き（他コードの既存データを保護）。
  - テスト用に _call_openai_api をモック差し替え可能。

- 市場レジーム判定モジュール（kabusys.ai.regime_detector）を追加。
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）判定。
  - マクロニュース抽出のためのキーワードリスト、LLM（gpt-4o-mini）呼び出し、再試行・フォールバック（API 失敗時は macro_sentiment=0.0）を実装。
  - レジームスコア合成（クリップ）と market_regime テーブルへの冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
  - ルックアヘッドバイアスを避ける設計（date 比較は target_date 未満等）・テスト可能性を考慮。

- データ処理・ETL 周り（kabusys.data）を追加。
  - calendar_management:
    - JPX カレンダー管理（market_calendar）用ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の一貫した営業日判定ロジックを提供。
    - DB にデータがない場合は曜日ベース（平日）でフォールバック。最大探索日数制限を実装して無限ループを防止。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得・バックフィル・健全性チェック・保存）。
  - pipeline / ETLResult:
    - ETL 実行結果を表現する dataclass ETLResult を実装（取得数・保存数・品質問題・エラー等を保持）。
    - ETLResult.to_dict() により品質チェック結果を辞書化して監査ログ等で利用可能。
    - 差分更新・バックフィル・品質チェックを行う ETL の設計方針を反映。

- リサーチ（kabusys.research）を追加。
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER、ROE）等のファクター計算関数を提供（calc_momentum / calc_volatility / calc_value）。
    - DuckDB を用いた SQL ベースの実装、データ不足時の None 処理、営業日スキャン範囲設計。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、統計サマリー（factor_summary）、ランク変換（rank）等を実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - research パッケージで主要ユーティリティを再エクスポート（zscore_normalize 等を含む）。

Changed
- （初回リリースのため履歴なし）

Fixed
- （初回リリースのため履歴なし）

Security
- OpenAI API キーは引数で注入可能とし、環境変数 OPENAI_API_KEY を補完的に参照。未設定時は明示的に ValueError を発生させることで誤った無限フェイル隠蔽を防止。
- .env 読み込み時に OS 環境変数を保護する仕組みを導入（protected set）。

Notes / 実装上の重要なポイント
- ルックアヘッドバイアス回避: news_nlp、regime_detector、research モジュールは内部で datetime.today() / date.today() を参照せず、呼び出し側から target_date を渡す設計。
- OpenAI 呼び出し部分はテスト容易性を考慮して内部関数（_call_openai_api）を patch 可能に実装している。
- DuckDB への書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）を利用し、部分失敗時の既存データ保護や ROLLBACK エラー時のログ出力を考慮。
- 外部依存を最小化（pandas 等に依存せず純 Python + DuckDB で実装）。
- デフォルトや安全フェイルバック（例: データ不足時の ma200_ratio=1.0、LLM 失敗時の macro_sentiment=0.0）を多用して処理が止まりにくい設計になっている。

開発者向けメモ
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env ロードを無効化できる。
- OpenAI 呼び出しや外部 API をモックすることでユニットテストを容易に実装できる（各モジュールにその旨コメントあり）。

今後の予定（提案）
- ai_scores / market_regime 等のテーブルスキーマを CHANGELOG に明示化しておくと移行時に有用。
- エンドツーエンドの ETL + モデル評価パイプライン用のサンプル CLI／ジョブスクリプトを追加。
- 追加の品質チェックルールやアラート（監視・通知）を強化。

--- 

（注）上記は提供されたコードをもとに機能・設計意図を推測して作成した CHANGELOG です。実際のコミット履歴やリリース日付はソース管理の履歴に基づいて適宜調整してください。