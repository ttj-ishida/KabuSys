Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣例に従います。

[Unreleased]
------------

（現在未解放の変更はここに記載してください）

0.1.0 - 2026-04-02
------------------

初回公開リリース。以下を実装・追加しました。

Added（追加）
- パッケージ基盤
  - kabusys パッケージを初期実装。バージョンを __version__ = "0.1.0" として公開。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定（kabusys.config）
  - .env ファイルと OS 環境変数から設定を自動ロードする仕組みを実装。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
  - .env パーサーを実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応。
    - 無効行（空行・コメント）を無視。
  - 環境向け設定ラッパー Settings を提供（プロパティ経由でアクセス）。
    - 必須設定を要求する _require() を実装（未設定時は ValueError）。
    - J-Quants / kabuステーション / Slack / データベースパス / 監視閾値 / システム設定（KABUSYS_ENV, LOG_LEVEL）等のプロパティを実装。
    - デフォルト値を備え、値検証（有効な env 値・ログレベル）を行う。
    - デフォルト DB パス: DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db。
    - 監視 PID ファイルや CPU/MEM/DISK 閾値のデフォルト値を提供。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を利用して銘柄ごとのニュースセンチメントを算出して ai_scores テーブルに書き込む処理を実装。
    - バッチ処理（最大 20 銘柄/チャンク）、チャンク内は記事数・文字数でトリム。
    - JSON Mode のレスポンス検証、スコアクリップ（±1.0）、部分成功時の DB 書換（DELETE→INSERT）により冪等性と部分障害耐性を確保。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実施。非再試行エラーはスキップして継続（フェイルセーフ）。
    - タイムウィンドウ: JST 前日15:00〜当日08:30（DB では UTC で比較）。
    - datetime.today()/date.today() を参照しない設計でルックアヘッドバイアスを防止。

  - regime_detector.score_regime
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とニュース由来のマクロセンチメント（重み30%）を合成し、market_regime テーブルへ日次で書き込む機能を実装。
    - マクロセンチメントは news_nlp 側と同様に OpenAI（gpt-4o-mini）で JSON を要求し、リトライ/フォールバック（失敗時 macro_sentiment=0.0）を実装。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の順で冪等性を確保。失敗時は ROLLBACK を試みる。
    - ルックアヘッドバイアス対策（prices_daily クエリで date < target_date 等）を徹底。

- データモジュール（kabusys.data）
  - calendar_management
    - market_calendar を元に営業日判定や次/前営業日の計算、期間内営業日取得、SQ判定などのユーティリティを実装。
    - DB にカレンダーがない場合は曜日ベース（土日を休業日）でフォールバックするロジックを提供。
    - calendar_update_job により J-Quants API からの差分取得→market_calendar への冪等保存（バックフィル・健全性チェック含む）を実装。
    - 探索上限日数（_MAX_SEARCH_DAYS）等で無限ループを防止。

  - pipeline / ETL
    - ETLResult データクラスを実装し、ETL の取得件数・保存件数・品質問題・エラー一覧を収集して返却。
    - 差分更新・バックフィル・品質チェックの設計（詳細ロジックは pipeline モジュール内に準備）。
    - jquants_client と quality モジュールを統合する設計になっている（save_* / fetch_* を利用）。

  - etl を再エクスポート（kabusys.data.etl: ETLResult）。

- 研究モジュール（kabusys.research）
  - factor_research
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を用いてモメンタム・ボラティリティ・バリュー系ファクターを計算。
    - 各関数は (date, code) をキーとする dict リストを返す。データ不足時は None を返す設計。
  - feature_exploration
    - calc_forward_returns（ホライズン指定で将来リターン取得）、calc_ic（スピアマンランク相関による IC 計算）、factor_summary（統計要約）、rank（平均ランクに基づく順位付け）を実装。
    - pandas 等に依存しない、標準ライブラリと DuckDB SQL の組合せで実装。
  - research パッケージの __all__ に主要関数を公開。
  - zscore_normalize を data.stats から再エクスポート（準備済み）。

Changed（変更）
- なし（初回リリースのため）。

Fixed（修正）
- なし（初回リリースのため）。

Security（セキュリティ）
- 環境変数の自動ロードで OS 側の既存環境変数が保護されるよう protected set を導入（.env 読み込み時の上書き制御）。
- OpenAI API キーの取り扱い:
  - score_news / score_regime は api_key 引数を受け取り、指定がない場合は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して明示的に要求。
- .env ファイルの読み取り失敗は警告で扱い、致命的に停止させない。

Notes（注意事項・移行メモ）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings を通じて必須（呼び出し側は .env を準備してください）。
- 自動 .env ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時推奨）。
- OpenAI 呼び出しは gpt-4o-mini を想定しており、レスポンスは JSON モードを利用するよう設計されています。API 仕様やモデルが変わる場合は各 _call_openai_api の実装を更新してください。
- DB 書き込みは冪等性を意識して設計されていますが、DuckDB のバージョン依存（executemany の空リスト制約など）があるため、本番環境での互換性確認を推奨します。
- 本リリースでは外部への実際の注文発注（execution）やモニタリング UI などは含まれていません（将来的な拡張点）。

既知の制約 / 将来の改善点
- news_nlp と regime_detector はそれぞれ独立して OpenAI 呼び出し用のプライベート関数を持つ（テスト容易性・モジュール結合低減のため）。将来的に共通化する場合はインターフェースを検討する必要があります。
- ETL pipeline の一部（fetch/save 実装の細部）は jquants_client 実装に依存しており、API の仕様変更に応じて更新が必要です。
- calendar_update_job の J-Quants API 呼び出しは外部からの例外に対して堅牢だが、API サイドのデータ不整合に対する追加の品質チェックを検討中。

Copyright
---------
本 CHANGELOG はリポジトリ内のソースコードから推測して作成しています。実際の変更履歴やリリースノートはプロジェクト運用者が適宜編集してください。