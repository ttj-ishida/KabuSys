# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

最新: Unreleased
=============

0.1.0 - 2026-04-04
------------------

初回公開リリース — 日本株自動売買システム「KabuSys」v0.1.0

Added
- パッケージ骨格を追加
  - パッケージ名: kabusys、バージョン: 0.1.0
  - 主要サブパッケージ: data, research, ai, (strategy, execution, monitoring を __all__ に含む)

- 環境設定 / .env 管理 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env のパースは export 形式、コメント、シングル/ダブルクォート、バックスラッシュエスケープ等をサポート。
  - OS 環境変数を保護する protected 機能（.env の上書きを制御）。
  - 必須環境変数取得ヘルパー _require。
  - Settings クラスを提供し、J-Quants/OpenAI/LINE/kabuステーション等の設定をプロパティで取得。
  - デフォルト値（KABUSYS_ENV, LOG_LEVEL, 各種パス/閾値など）と入力検証（env 値・ログレベルの許容値）を実装。
  - is_live / is_paper / is_dev の判定ヘルパーを提供。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols を集約し、銘柄ごとにニュースをまとめて OpenAI（gpt-4o-mini, JSON Mode）へ送信してセンチメントを算出。
  - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window に実装。
  - バッチ処理（最大 20 銘柄 / リクエスト）、1 銘柄あたりの最大記事数および文字トリムを実装（トークン肥大化対策）。
  - リトライ（429/ネットワーク/タイムアウト/5xx）と指数バックオフ、失敗時はスキップして継続（フェイルセーフ）。
  - レスポンスの厳格なバリデーション（JSON 抽出、results 配列、各要素の code/score 検証、数値性チェック、±1.0 クリップ）。
  - 成功したスコアのみ ai_scores テーブルへ置換的に書き込み（DELETE（各 code ごと）→ INSERT）。DuckDB の executemany 空リスト制約に配慮。
  - テスト容易性: OpenAI 呼び出しは _call_openai_api を介しており、ユニットテスト時にモック可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
  - prices_daily からの MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを回避。
  - マクロニュース抽出はキーワードベース（デフォルトセットあり）で最大件数制限。
  - OpenAI 呼び出しのリトライ／バックオフを実装、API 失敗時は macro_sentiment=0.0 でフォールバック（例外を投げず継続）。
  - market_regime テーブルへ冪等に書き込む処理を実装（BEGIN / DELETE / INSERT / COMMIT）。DB 書き込み失敗時は ROLLBACK を試みて例外を上位へ伝達。
  - テスト容易性: news_nlp とは別実装の _call_openai_api を用意しモジュール結合を低減。

- リサーチ機能（kabusys.research）
  - ファクター計算: calc_momentum, calc_volatility, calc_value
    - Momentum: 1M/3M/6M リターン、200日 MA 乖離（不足時は None）。
    - Volatility: 20日 ATR（true range の NULL 伝播制御）、相対 ATR、出来高/売買代金関連指標。
    - Value: raw_financials からの EPS/ROE を用いた PER/ROE 計算（EPS が 0/欠損は None）。
  - 特徴量探索: calc_forward_returns（任意ホライズン、入力検証あり）、calc_ic（スピアマンランク相関）、rank（同順位は平均ランクで処理）、factor_summary（count/mean/std/min/max/median）。
  - DuckDB SQL を主に利用し、外部ライブラリへ依存しない実装。
  - 欠損データや特殊ケースへの defensive な実装（None 処理、有限値チェックなど）。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - market_calendar を利用した営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバック。一貫性を保つ探索ロジック（最大探索日数制限）。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、健全性チェック、API エラーのハンドリング）。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult dataclass を公開（pipeline の実行結果集約、品質問題やエラーの一覧化を含む）。
    - 差分更新、バックフィル、品質チェック周りの設計（Fail-Fast ではなく品質問題を収集して呼び出し元判断）。
    - DuckDB テーブル存在チェック・最大日付取得等のユーティリティを実装。
  - jquants_client を通じた外部データ取得を想定した実装（fetch/save の抽象化を前提）。

- ロギング・ワーニング
  - 各処理において状態/異常時の logger 出力を整備（INFO/DEBUG/WARNING/exception を適所で使用）。

Changed
- （初版のため履歴なし）

Fixed
- （初版のため履歴なし）

Security
- （初版のため履歴なし）

Notes / 設計上の重要点
- ルックアヘッドバイアス防止のため、全ての「当日基準」処理は datetime.today()/date.today() への直接依存を避け、target_date を明示的に受け取る設計にしている。
- OpenAI 呼び出し周りは JSON Mode を利用し、レスポンスのパースが壊れるケース（前後余計なテキスト等）へ対処するロジックを含む。
- DuckDB のバージョン差異（executemany の空リストバインド等）に配慮した実装を行っている。
- テストのしやすさを考慮し、外部 API 呼び出し点（OpenAI 呼び出し等）に対する差し替えポイントを明示的に用意している。

今後の予定（短期）
- strategy / execution / monitoring の実装拡張（現在は __all__ に名前があるが中身は段階的実装予定）。
- ai モデルのパラメータチューニングと追加バリデーション。
- ETL の品質チェックルールの拡充と監視アラート連携。

--- 

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノート作成時はコミット履歴やリリースプロセスに基づいて更新してください。