# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマットや用語は https://keepachangelog.com/ja/ に準拠しています。

なお、本 CHANGELOG は提供されたソースコードの内容から機能・設計上の差分を推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-31

Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - 公開モジュール: data, strategy, execution, monitoring（パッケージのエントリポイントに __all__ を定義）
  - パッケージバージョン: 0.1.0

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
  - プロジェクトルート自動検出: .git または pyproject.toml を起点に探索（パッケージ配布後も CWD に依存しない挙動）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）。
  - .env パーサーの強化:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応
    - インラインコメントの取り扱い（クォート外の '#' は直前が空白/タブのときのみコメントと判定）
  - 既存 OS 環境変数を保護するための protected オプションを実装（.env の上書き制御）。
  - Settings クラスを提供し、主要設定（J-Quants トークン、kabu API、Slack トークン、DB パス、環境・ログレベル等）をプロパティで取得可能。
  - KABUSYS_ENV / LOG_LEVEL の値検証を実装（許容値の検証で誤設定検出）。

- データ層（kabusys.data）
  - ETL パイプライン基盤（kabusys.data.pipeline）を追加
    - ETLResult dataclass（取得/保存件数、品質問題、エラーの集約、has_errors/has_quality_errors/ to_dict を含む）
    - 差分取得、バックフィル、品質チェックの設計方針を反映
    - DuckDB を想定したテーブル存在確認 / 最大日付取得ユーティリティ
  - ETL 用の公開インターフェース再エクスポート（kabusys.data.etl: ETLResult）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - 営業日判定: is_trading_day, is_sq_day
    - 隣接営業日の検索: next_trading_day, prev_trading_day
    - 期間内の営業日一覧取得: get_trading_days
    - 夜間バッチ更新 job: calendar_update_job（J-Quants API から差分取得 → 保存）
    - DB がまばらな場合でも曜日ベースのフォールバックを行う設計
    - 最大探索日数やバックフィル、健全性チェック（将来日付の異常検出）を実装
    - jquants_client (jq) を通じた fetch/save の呼び出しを想定

- AI 機能（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - score_news(conn, target_date, api_key=None): raw_news と news_symbols から記事を集約し、銘柄ごとのセンチメント ai_score を生成して ai_scores テーブルへ保存
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST に対応（UTC 変換済みの範囲を使用）
    - 記事のトリム / 銘柄ごとの最大記事数・最大文字数によるトークン肥大化対策（デフォルト: 最大記事数 10、最大文字数 3000）
    - バッチ送信（1 API コールあたり最大 20 銘柄）と JSON Mode を用いた厳格なレスポンス期待
    - リトライ/バックオフ戦略（429, ネットワーク断, タイムアウト, 5xx を対象）を実装
    - レスポンスバリデーション処理（JSON パース、results リスト、code の正規化、数値検証、±1.0 でクリップ）
    - 部分成功時の安全な DB 書き込み（該当コードのみ DELETE → INSERT）と DuckDB executemany の空リスト注意点に対応
    - テスト容易性のため OpenAI 呼び出しを patch 可能（内部 _call_openai_api を分離）
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - score_regime(conn, target_date, api_key=None): ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定・保存
    - MA200 は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）
    - マクロニュース抽出: タイトルベースのキーワードフィルタ（複数キーワードリストを定義）
    - OpenAI へのリクエストは明示的に再試行/バックオフ処理を実装、失敗時は macro_sentiment=0.0 にフォールバック（例外を投げず続行）
    - レジームスコア合成としきい値によるラベリング、market_regime テーブルへの冪等的トランザクション書込み（BEGIN / DELETE / INSERT / COMMIT と ROLLBACK 処理）
    - テスト容易性のため呼び出し箇所を差し替え可能な設計

- リサーチ・ファクター群（kabusys.research）
  - factor_research モジュールを追加
    - calc_momentum(conn, target_date): 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）を計算
    - calc_volatility(conn, target_date): 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算
    - calc_value(conn, target_date): raw_financials から最新財務データを取り込み PER（EPS が無効な場合は None）、ROE を計算
    - 各関数は prices_daily / raw_financials のみ参照し、本番の発注 API 等にはアクセスしない設計
    - 戻り値は (date, code) キーを含む dict のリストで返却
  - feature_exploration モジュールを追加
    - calc_forward_returns(conn, target_date, horizons=None): 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンのランク相関（IC）を計算。十分なデータがなければ None を返す
    - rank(values): 同順位は平均ランクで処理、浮動小数の丸め（round(v,12)）で ties を安定化
    - factor_summary(records, columns): count/mean/std/min/max/median を算出する統計サマリー
  - 研究用ユーティリティ（kabusys.research.__init__）で主要関数を再エクスポート

- 共通インフラ・設計上の配慮
  - DuckDB を主要データストアとして想定（DuckDB 接続引数を多くの関数が受け取る）
  - OpenAI SDK（モデル: gpt-4o-mini）を用いた JSON Mode での応答処理を採用
  - ルックアヘッドバイアス防止: datetime.today()/date.today() を直接参照しない実装方針を採用（target_date を明示的に受け取る）
  - トランザクション処理: DB 書き込みは基本的に BEGIN / COMMIT / ROLLBACK で冪等性と整合性を確保
  - ロギングとエラーハンドリングを広く導入（API 失敗時のフォールバックや警告ログ）
  - テスト容易性のため内部 API 呼び出し点を patch 可能に分離

Fixed
- （初期リリースのため該当なし）

Changed
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Notes / Known limitations
- OpenAI API キー（環境変数 OPENAI_API_KEY）や各種外部 API キーが必須の処理がある。未設定時は明示的な ValueError を送出。
- DuckDB 固有の executemany の空リスト制約に対応した実装がある（空リストでの executemany を避けるコード経路）。
- news_nlp/regime_detector は外部 API 呼び出しに依存するため、API 料金・レートリミット・モデル応答のばらつきに注意。
- strategy / execution / monitoring の具体的な実装は本変更点のスコープ外（パッケージエントリは用意されているが詳細は未記載）。

---

作成者注:
- 本 CHANGELOG は提供されたソースコードから機能・意図を推測してまとめたものです。実際のリリースノートではコミット履歴やリリース時の差分に基づいて追記・修正してください。