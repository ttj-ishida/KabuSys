Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。  
（以下の変更点は提示されたコードベースから推測して記載しています）

Unreleased
----------

- なし

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初期リリース（kabusys v0.1.0）。
  - パッケージ公開情報: src/kabusys/__init__.py に __version__ = "0.1.0"。
- 環境設定管理モジュール（kabusys.config）
  - .env ファイルと OS 環境変数の読み込みロジックを実装（.env, .env.local の優先度処理）。
  - .env パーサー実装: コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に探索（CWD に依存しない）。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意（テスト向け）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等のプロパティを取得可能に。
  - 必須環境変数未設定時に例外を投げる _require 関数を導入。
  - env, log_level の検証（許容値チェック）を実装。

- AI モジュール（kabusys.ai）
  - news_nlp: ニュースを集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores テーブルへ書き込む機能を実装。
    - ニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST 相当の UTC 範囲）。
    - 1 銘柄あたり記事数・文字数の上限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）でトリム。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄/コール）、JSON mode の利用、レスポンスバリデーション実装。
    - 再試行（429・ネットワーク・タイムアウト・5xx）を指数バックオフで実行。
    - スコアは ±1.0 にクリップ。部分成功でも既存スコアを保護するため書き込みは対象コードのみ DELETE→INSERT。
    - テスト容易性のため OpenAI 呼び出し点に差し替え用フック（_call_openai_api）あり。
  - regime_detector: ETF 1321 の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して市場レジーム（bull/neutral/bear）を判定・market_regime に書き込む機能を実装。
    - ma200_ratio 計算（ルックアヘッド防止のため target_date 未満のみ参照）とフェイルセーフ（データ不足時は中立=1.0）。
    - マクロニュース抽出（キーワードリスト）と LLM による macro_sentiment の評価（JSON 出力期待）。
    - API 再試行・エラー処理（RateLimit/接続/タイムアウト/5xx など）を実装、失敗時は macro_sentiment=0.0 で継続。
    - 冪等的な DB 書き込み（BEGIN/DELETE/INSERT/COMMIT）を行う。

- データモジュール（kabusys.data）
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - market_calendar が未取得の場合は曜日ベース（土日休み）でフォールバック。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、保存処理）。
    - DB 存在チェック・NULL 値への警告等の堅牢化。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを実装し ETL 実行結果の構造化（品質問題・エラー列挙を含む）。
    - 差分取得、バックフィル、品質チェックの方針をコード化（jquants_client と quality モジュールの利用を想定）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- Research モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離の算出。
    - calc_volatility: 20 日 ATR、相対 ATR、平均売買代金、出来高比率の算出。
    - calc_value: raw_financials から取得した財務指標に基づく PER/ROE の算出（EPS 0 や欠損は None）。
    - 各関数は DuckDB クエリベースで実装し、外部 API へはアクセスしない。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）を実装。データ不足時は None。
    - rank: 値リストをランクに変換（同順位は平均ランク、丸め処理で ties を安定化）。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を算出。
  - research パッケージは上記関数を再エクスポートする __init__ を用意。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の自動ロード時に既存 OS 環境変数を保護する仕組み（protected set による上書き防止）を実装。
- OpenAI API キー未設定時は ValueError を明示的に発生させ、キーの誤使用を防止。

Performance
- DuckDB のウィンドウ関数や一括 SQL を多用し、計算をデータベース側で効率的に行う設計。
- ニュース処理は銘柄単位でチャンク化して API 呼び出しを行い、リクエスト数を制御。

Design / Notes
- ルックアヘッドバイアス対策: いずれのスコア算出関数も datetime.today()/date.today() を内部参照せず、必ず引数 target_date に依存するよう実装。
- フェイルセーフ: 外部 API（OpenAI, J-Quants）失敗時は全体を停止せず個別スコアをゼロ/スキップして継続する設計。
- テスト容易性: OpenAI 呼び出し点に差し替え用関数（_call_openai_api）を用意し、unittest.mock.patch によるモックが可能。
- DuckDB バインドの互換性考慮（executemany に空リスト渡さない等）。
- 多くの箇所で冪等性を重視した DB 書き込み（DELETE→INSERT や ON CONFLICT など）を採用。

Deprecated
- なし

Removed
- なし

Breaking Changes
- なし（初期リリース）

Authors / Contributors (推測)
- コード中の設計ノート・コメントに基づき、金融データパイプライン・機械学習モデルの運用経験を持つ開発者による実装と推測されます。

注記
- 上記は提示されたソースコードからの推測に基づく CHANGELOG です。実際のリリースノート作成時はコミット履歴や実際の変更差分（テスト、ドキュメント、CI 設定等）を参照して補完してください。