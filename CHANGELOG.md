# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/) の形式に従います。  
このファイルはコードベース（src/kabusys）から推測して作成した初期リリース向けの変更履歴です。

なお、バージョン番号はパッケージの __version__ (0.1.0) に合わせています。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-31

Added
- コアパッケージの初期実装
  - パッケージメタ情報（kabusys.__init__）を追加。公開サブパッケージ: data, research, ai, execution, monitoring, strategy（うち提示されたファイル群を実装）。
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - エクスポート形式（export KEY=val）対応、クォート処理、行内コメントの取り扱いを考慮した .env パーサ実装。
  - OS 環境変数を保護する protected キー概念を導入し、.env.local で上書き可能にする一方で既存の OS 環境変数を誤って上書きしないよう配慮。
  - 自動ロード抑止用フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート。
  - 必須キー取得ヘルパー _require、環境値検証（KABUSYS_ENV, LOG_LEVEL）を実装。
  - デフォルトパスと監視閾値（CPU/MEM/DISK）などの設定プロパティを提供。
- データプラットフォーム（kabusys.data）
  - ETL パイプライン関連の基盤
    - ETL 結果を表現する dataclass ETLResult を追加（取得件数、保存件数、品質問題、エラー一覧などを保持）。
    - pipeline モジュールで差分取得・保存・品質チェックを行う設計を実装（差分更新、backfill、品質チェックの集約など）。
    - DuckDB を前提とした実装で、実行互換性（executemany の空リスト制約）を考慮。
  - 市場カレンダー管理（calendar_management）
    - market_calendar テーブルを用いた営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB登録値優先、未登録日は曜日ベースのフォールバックを行う一貫した挙動。
    - 夜間バッチ更新 job（calendar_update_job）を実装：J-Quants から差分取得し冪等的に保存、バックフィル・健全性チェックを実施。
- 研究（research）モジュール
  - ファクター計算（factor_research）
    - モメンタム（1M/3M/6M リターン、200日MA乖離）、ボラティリティ（20日ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB クエリで計算する関数を実装。
    - データ不足時の None 処理やログ出力を備える。
  - 特徴量解析ユーティリティ（feature_exploration）
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証）。
    - IC（Information Coefficient）計算（スピアマンのランク相関）とランク関数（rank）。
    - ファクター統計サマリ（factor_summary）。
  - zscore_normalize を data.stats から再エクスポート。
- AI（kabusys.ai）
  - ニュース NLP（news_nlp）
    - raw_news と news_symbols を元に銘柄別に記事を集約し、OpenAI（gpt-4o-mini、JSON Mode）へバッチ送信して銘柄ごとのセンチメント（ai_score）を算出・ai_scores テーブルへ書き込む実装を追加。
    - チャンク処理（最大 20 銘柄/回）、1 銘柄あたりの最大記事数/文字数制限、429/ネットワーク断/タイムアウト/5xx に対する指数バックオフによるリトライ、応答の厳密なバリデーションを実装。
    - API エラー時はスキップして処理継続するフェイルセーフ設計、部分失敗時に既存スコアを保護するための部分的 DELETE→INSERT ロジックを採用。
  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（OpenAI による LLM 評価、重み 30%）を合成して日次でレジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする実装を追加。
    - マクロ記事フィルタリング用キーワード群、LLM 呼び出しのリトライ/フォールバック（API 失敗時 macro_sentiment=0.0）を実装。
    - ルックアヘッドバイアス防止のため、内部で datetime.today()/date.today() を参照せず、クエリでは target_date 未満のデータのみ使用。
- 汎用設計上の配慮
  - ルックアヘッドバイアス防止: ほとんどの機能が target_date を外部から受け取り、内部で現在日時を参照しない実装。
  - DuckDB の互換性（executemany の空リスト制約など）を考慮した実装多数。
  - DB 書き込みは冪等性を重視（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK を試行）。
  - OpenAI 呼び出し箇所はテスト容易性のため置換可能（内部の _call_openai_api をモック可能に設計）。

Changed
- 初期リリースのため該当なし（最初の公開機能群をまとめて追加）。

Fixed
- 初期リリースのため該当なし。

Deprecated
- なし。

Removed
- なし。

Security
- OpenAI API キーの取り扱いは引数で注入可能（api_key）か環境変数 OPENAI_API_KEY を利用する形で実装。キー未設定時は ValueError を送出して明示的に取り扱う。

Notes（注記）
- 一部モジュールは外部クライアント（jquants_client 等）を参照する設計になっており、実動作には外部 API クライアント実装や DB スキーマ（prices_daily, raw_news, ai_scores, market_calendar 等）が必要です。
- monitoring / execution / strategy 等のサブパッケージはパッケージの __all__ に含まれますが、本CHANGELOG作成時に提示されたファイル群では実装の詳細が含まれていません。実装が追加された場合は別途追記してください。

---

以上が現在のコードベース（src/kabusys）から推測して作成した CHANGELOG.md です。追加のコミット履歴やリリース日付の変更、より詳細な変更点（バグ修正・小さな改善など）があれば、次バージョンで追記します。