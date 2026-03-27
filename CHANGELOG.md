CHANGELOG
=========
すべての重要な変更を記録します。フォーマットは「Keep a Changelog」に準拠します。  
このファイルは、コードベースの内容から推測して作成した初期リリース向けの変更履歴です。

フォーマット
-----------
- 変更はカテゴリ（Added, Changed, Fixed, Deprecated, Removed, Security）別に記載します。
- 各エントリには対象モジュール／機能と要点（振る舞い、設計方針、制約）を明記しています。

Unreleased
----------
（現時点で未リリースの変更はありません）

[0.1.0] - 2026-03-27
-------------------
初期リリース（コードベースの初公開相当）。以下の主要機能と実装方針を含みます。

Added
-----
- 全体
  - kabusys パッケージの初期公開。パッケージメタ情報として __version__ = "0.1.0" を設定。
  - パッケージ外部インターフェースとして data, strategy, execution, monitoring を __all__ にエクスポート（モジュール・サブパッケージの公開意図を明示）。

- 設定管理（kabusys.config）
  - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装。プロジェクトルートは .git または pyproject.toml を基準に探索して特定。
  - .env / .env.local の読み込み順序を実装（OS 環境変数を保護する protected セットを用いた上書き制御）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート（テスト等で使用）。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / システム設定（env, log_level, is_live 等）向けプロパティを提供。環境変数の必須チェックとバリデーションを行う（未設定時に ValueError を発生）。

- データ関連（kabusys.data）
  - calendar_management:
    - JPX カレンダー管理と営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar が未取得の場合の曜日ベースフォールバックと、DB 登録値優先の一貫した判定ロジックを実装。
    - 夜間バッチ更新 job（calendar_update_job）を実装。J-Quants API から差分取得して冪等的に保存し、バックフィル・健全性チェックを含む。
  - pipeline / ETL:
    - ETLResult データクラスを実装し、ETL 実行結果（取得数、保存数、品質問題、エラーメッセージ等）を集約。
    - jquants_client と quality モジュールと連携する ETL パイプライン方針を反映（差分更新、バックフィル、品質チェックの設計方針を取り入れた実装方針を備える）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ/流動性（20 日 ATR、平均売買代金、出来高比率）、バリュー（PER, ROE）を計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB を使った SQL 中心の実装。データ不足時の扱い（None 返却）やウィンドウサイズ・スキャン範囲の設計を含む。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns）、IC（スピアマンランク相関）計算（calc_ic）、ランク変換ユーティリティ（rank）、ファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存せず標準ライブラリと DuckDB で実装。入力検証（horizons の範囲チェック等）あり。
  - research パッケージの公開 API を整備（関数の再エクスポートを __all__ に設定）。

- AI（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols から銘柄ごとに記事を集約し（前日15:00 JST〜当日08:30 JST のウィンドウ）、OpenAI（gpt-4o-mini）へバッチで送信して銘柄ごとのセンチメント（ai_score）を ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（最大 20 銘柄 / リクエスト）、トリミング（記事数／文字数制限）、JSON Mode の応答パース、レスポンスバリデーション、スコアの ±1.0 クリップ、部分成功時の DB 置換戦略（DELETE → INSERT）を実装。
    - ネットワーク・429・タイムアウト・5xx に対する指数バックオフによるリトライを実装（リトライ上限あり）。API 失敗時はそのチャンクをスキップして処理継続（フェイルセーフ）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等的に書き込む処理を実装。
    - prices_daily からの MA 計算、raw_news からマクロキーワードでの抽出、OpenAI 呼び出し（gpt-4o-mini + JSON mode）、スコア合成、閾値判定、DB トランザクション（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 失敗時は macro_sentiment = 0.0 で継続するフェイルセーフを備える。こちらもテスト用に _call_openai_api の差し替えが可能。

Changed
-------
- （初回リリースのため履歴なし）

Fixed
-----
- 公平性・リスク軽減設計
  - AI 系処理（news_nlp, regime_detector）で datetime.today() / date.today() を直接参照せず、明示的な target_date パラメータを用いることでルックアヘッドバイアスを排除（分析・バックテスト向けに重要）。
- DuckDB 互換性の考慮
  - executemany に空パラメータリストを渡せない DuckDB の制約を考慮して、空リスト時に実行しないガードを実装（ETL / ai の INSERT/DELETE 処理で対応）。
- ロバストネス
  - OpenAI API レスポンスの JSON パースが失敗するケース（前後に余計なテキストが混入する等）を想定した復元処理を実装（最外側の {} を抽出して再パース）。
  - API 呼び出し失敗時は例外で abort せずログに記録してフォールバック（0.0 やスキップ）することで処理継続を保証。

Deprecated
----------
- （初回リリースのためなし）

Removed
-------
- （初回リリースのためなし）

Security
--------
- 環境変数管理
  - .env 読み込み時に既存の OS 環境変数を保護する仕組み（protected set）を実装し、意図しない上書きを避ける設計。
  - 必須トークン（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）は Settings の _require により未設定時に ValueError を発生させる。
  - 自動.env読み込みの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を用意。

Notes / 実装上の重要ポイント
---------------------------
- テスト性: OpenAI 呼び出しを行う内部ヘルパー（_kabusys.ai.*._call_openai_api）を unittest.mock.patch で差し替え可能にしており、ユニットテストで外部依存を排除しやすい設計。
- フェイルセーフ: AI API や外部 API の一時障害を理由に全体処理を停止させない方針（失敗したチャンクのみスキップ、デフォルトスコアを用いる等）。
- DB トランザクション: 書き込み処理は明示的な BEGIN / COMMIT / ROLLBACK を用いた冪等的な保存を行い、部分失敗時に既存の重要データを不要に消さない設計（ai_scores や market_regime に適用）。
- 日付の扱い: すべての日付は timezone を混入させない date / naive datetime で扱う方針を採用（UTC/指定変換のコメントあり）。
- DuckDB 前提: 多くの処理は DuckDB 接続（DuckDBPyConnection）を前提として実装されているため、実行時は DuckDB を準備する必要あり。

将来の改善案（コードから推測）
------------------------------
- strategy / execution / monitoring パッケージの実装（現状はエクスポートのみ示唆）。実トレードフローや監視機構の追加。
- AI モデルやプロンプトのチューニング、モデル選択の動的切替、より細かな品質チェックの拡張。
- ETL の部分的再実行・差分解析をより柔軟にする UI/CLI あるいはジョブスケジューラ統合。

----------------------------------------
（この CHANGELOG はリポジトリ内のソースコードの実装内容・設計コメントから推測して作成しています。実際のコミット履歴やリリースノートに合わせて調整してください。）