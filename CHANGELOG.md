CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
コードベースの内容から推測して作成した初期リリースの変更履歴です。

Unreleased
----------

- (現在のところ未リリースの変更はありません)

[0.1.0] - 2026-03-29
--------------------

初期リリース — 日本株自動売買 / データ基盤 / 研究用ユーティリティ群の基本機能を実装。

Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョン 0.1.0 を定義。
  - public API として data, research, ai, monitoring, strategy, execution を想定したモジュール構成を公開（__all__）。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを実装。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグを提供（テスト時の利便性向上）。
  - .env 行パーサーを実装（コメント・export、シングル/ダブルクォート、バックスラッシュエスケープやインラインコメントの取り扱い対応）。
  - 環境変数の必須チェック（_require）と設定ラッパー Settings を追加。J-Quants / kabu / Slack / DB パス / 環境モード /ログレベル等のプロパティを用意。
  - KABUSYS_ENV や LOG_LEVEL の値検証（許容値チェック）を実装。

- データ基盤（kabusys.data）
  - calendar_management:
    - JPX 市場カレンダー管理機能を実装（market_calendar テーブルを参照）。
    - 営業日判定（is_trading_day）、前後営業日取得（next_trading_day / prev_trading_day）、期間内営業日取得（get_trading_days）、SQ日判定（is_sq_day）を提供。
    - 夜間バッチ更新ジョブ calendar_update_job を実装。J-Quants クライアント経由で差分取得→冪等保存（ON CONFLICT 相当）を行う。
    - カレンダーデータ欠如時の曜日ベースフォールバック、最大探索日数制限、バックフィル・健全性チェック等を実装。
  - ETL パイプライン:
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。
    - pipeline モジュールに差分取得・保存・品質チェックのためのユーティリティを実装。最終取得日の取得、バックフィル、品質チェック（quality モジュール連携）などを実装。

- 研究用ユーティリティ（kabusys.research）
  - factor_research:
    - モメンタムファクター（1M/3M/6M リターン、200 日 MA 乖離）計算（calc_momentum）。
    - ボラティリティ・流動性ファクター（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）計算（calc_volatility）。
    - バリューファクター（PER, ROE）計算（calc_value）。
    - DuckDB SQL を用いた高効率な集計を実装。データ不足時は None を返す等の安全策あり。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意ホライズン、入力検証あり）。
    - IC（Information Coefficient、Spearman ρ）計算（calc_ic）。
    - ランク関数（rank）とファクター統計サマリー（factor_summary）を実装。
  - データ処理ユーティリティ（zscore_normalize）は data.stats から再エクスポート。

- AI / NLP（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を使い、指定タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）内のニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）へバッチ送信し、センチメント ai_score を ai_scores テーブルへ書き込む。
    - チャンク処理（1 リクエスト最大 20 銘柄）、1 銘柄あたり記事数/文字数上限、レスポンス検証（JSON 抽出、results 構造検証、コード照合、数値チェック）、スコアクリッピング（±1.0）を実装。
    - ネットワーク断・429・タイムアウト・5xx は指数バックオフでリトライ、その他は失敗時にスキップするフェイルセーフ。
    - 書き込みは部分失敗時にも既存の他銘柄スコアを消さないように、対象コードに限定した DELETE → INSERT の冪等更新を実装（DuckDB の制約考慮）。
    - テスト時に差し替え可能な API 呼び出しラッパー（_call_openai_api）を用意。
  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）と、macro ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次で判定し、market_regime テーブルに書き込む処理を実装。
    - OpenAI 呼び出しは専用の _call_openai_api を用い、API エラー時は macro_sentiment=0.0 で継続するフェイルセーフを提供。
    - データアクセス時のルックアヘッド防止（target_date 未満のデータのみ参照）を徹底。

Changed
- 初回実装のため、後方互換性の変更履歴はなし（初期リリース）。

Fixed
- 初期リリースのため、既知のバグ修正履歴はなし。

Security
- 環境変数読み込み時に OS 環境変数を保護する protected セットを導入（.env.local により意図しない上書きを防止）。
- OpenAI API キーや各種トークンは環境変数経由で取得し、必須未設定時は ValueError を発生させる（明示的な失敗で安全性を確保）。

Notes / 開発者向け補足
- 意図的な設計原則:
  - ルックアヘッドバイアス防止のため、datetime.today() / date.today() 参照をスコープ内に直接使わず、すべての関数は target_date 引数を受け取る。
  - API 呼び出しはリトライ・バックオフやタイムアウトを備え、失敗時は例外で止めずフォールバックする箇所がある（運用での頑健性重視）。
  - DuckDB をデータ層に使用し、SQL ウィンドウ関数を活用して効率的に集計・ラグ計算を行う。
  - テスト容易性のため、OpenAI 呼び出しを差し替え可能（unittest.mock.patch 想定）。
- 必須と思われる環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（モジュール使用に応じて必要）
- 将来の作業候補（今後の改善点・拡張候補、現状の設計から推測）
  - モデルやバッチサイズの設定を外部化して運用で調整可能にする。
  - ai モジュールの出力検証・監査ログの強化（発話ログの保存等）。
  - ETL の並列化や増分フェッチ戦略の詳細なメトリクス収集。
  - strategy / execution / monitoring モジュールの実装（パッケージ公開インターフェースとして既に見込みあり）。

---

本 CHANGELOG はコードベースの実装から推測して作成しています。実際のリリースノートや API 仕様・日付はプロジェクトの正式な管理情報に従ってください。