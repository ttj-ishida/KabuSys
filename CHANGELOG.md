CHANGELOG
=========

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠します。

フォーマット:
- 依頼者向けにコードベースの現在状態（初期リリース）をコード内容から推測して記載しています。
- バージョンはパッケージ内の __version__ に合わせて 0.1.0 としています。
- 日付は本出力日時 (2026-03-29) を使用しています。

[0.1.0] - 2026-03-29
-------------------

Added
- パッケージ基本構成を追加
  - kabusys パッケージの公開モジュール群を定義（data, strategy, execution, monitoring）。
  - __version__ = "0.1.0" を設定。

- 設定 / 環境変数管理（kabusys.config）
  - .env / .env.local をプロジェクトルートから自動読み込みする仕組みを実装。
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索して行うため、CWD に依存しない。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 読み込み優先順: OS 環境変数 > .env.local > .env。
  - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いに対応）。
  - 既存 OS 環境変数を保護する protected キー機構と override の挙動を実装。
  - Settings クラスを実装しアプリケーション設定をプロパティで提供（J-Quants トークン、kabu ステーション API、Slack、DB パス、環境種別、ログレベルなど）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）を実装。
    - is_live / is_paper / is_dev のヘルパーを提供。
    - 必須環境変数未設定時は ValueError を送出する _require を実装。

- AI モジュール（kabusys.ai）
  - news_nlp: ニュース記事を OpenAI (gpt-4o-mini) に送り銘柄毎のセンチメント ai_score を算出して ai_scores テーブルへ保存する一連処理を実装。
    - ニュース収集ウィンドウ計算（JST 前日15:00〜当日08:30 相当の UTC 変換）を calc_news_window で実装。
    - 記事集約（news_symbols 結合、銘柄ごとに最新 n 件を結合、文字数トリム）。
    - バッチ送信（_BATCH_SIZE: 最大20銘柄）・リトライ（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）・レスポンス検証・スコアクリップ（±1.0）。
    - DuckDB への書込みは idempotent（DELETE→INSERT）で実行し、部分失敗時に他コードの既存スコアを保護する実装を採用。
    - テスト容易性のため OpenAI 呼び出し部分を差し替え可能（ユニットテスト用のパッチ位置を明記）。
    - 空レスポンスやパース失敗時はフェイルセーフでスキップし続行する設計。
  - regime_detector: ETF（1321 日経225連動型）200日移動平均乖離とマクロニュースの LLM センチメントを組み合わせて市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む処理を実装。
    - ma200_ratio の計算（target_date 未満のデータのみ使用しルックアヘッドを防止）。
    - マクロニュース抽出（マクロキーワードでタイトルをフィルタ）、LLM によるセンチメントスコアリング、重み付け合成（MA:70% / Macro:30%）、閾値に基づくラベリング。
    - OpenAI 呼び出しに対してリトライ・バックオフを実装し、API 失敗時は macro_sentiment=0.0 をフォールバック。
    - DB へは BEGIN / DELETE / INSERT / COMMIT の冪等書き込みを行い、失敗時は ROLLBACK を実施。ロールバック失敗は警告ログを出力。
    - モジュール間の結合を避けるため、OpenAI 呼び出しの内部実装は news_nlp と別実装を保持（テストで差し替え可能）。

- Data モジュール（kabusys.data）
  - calendar_management: JPX マーケットカレンダー管理（market_calendar）と営業日判定ユーティリティを実装。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - カレンダーデータが存在しない場合は曜日ベース（土日休み）でフォールバック。
    - DB 値優先、未登録日は曜日フォールバックで一貫した判定を返す設計。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新する夜間ジョブを実装（バックフィル、健全性チェック、J-Quants クライアント利用）。
  - pipeline: ETL パイプラインのインターフェースと ETLResult データクラスを実装。
    - ETLResult に品質チェック結果 (quality_issues)、エラー収集、シリアライズ用 to_dict を実装。
    - 差分更新、バックフィル、品質チェックのための設計方針を反映（実装は pipeline 内で進行）。
  - etl: pipeline.ETLResult を再エクスポート。

- Research モジュール（kabusys.research）
  - factor_research: ファクター計算（モメンタム、ボラティリティ、バリュー等）を実装。
    - calc_momentum: 1M/3M/6M リターン、ma200_dev を計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を計算。
    - DuckDB を用いた SQL ベースの処理で、外部 API に依存しない実装。
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、rank ヘルパー、factor_summary（基本統計量）を実装。
    - calc_forward_returns: 指定ホライズンに対する複数リターンを一度に取得する効率的な SQL 実装。
    - calc_ic: factor と forward リターンのランク相関（Spearman ρ）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクで処理するための安定したランク変換。
    - factor_summary: count/mean/std/min/max/median を計算。

Changed
- （初期リリース）多くの設計方針をドキュメント文字列に明記（ルックアヘッドバイアス防止、テスト容易性、DuckDB 特有の注意点等）。

Fixed
- （初期リリース）なし（コード内に堅牢化処理・フォールバックを多数実装）。

Security
- 環境変数の取り扱いにおいて、既存の OS 環境変数を上書きしないデフォルト挙動と protected キーを導入。自動ロードを無効化するフラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。

Notes / Implementation details
- OpenAI API 関連
  - 使用モデル: gpt-4o-mini（news_nlp / regime_detector 共に JSON mode を利用し厳密な JSON 出力を期待）。
  - エラー処理: 429 / ネットワーク切断 / タイムアウト / 5xx サーバーエラーに対する指数バックオフリトライを採用。非リトライ対象エラーや最終失敗時はフェイルセーフで 0.0（中立）やスキップを返す。
  - テスト用に内部呼び出し関数（_call_openai_api 等）を patch して差し替え可能に設計。

- データベース（DuckDB）関連
  - DuckDB の executemany における空パラメータ制約を考慮し、空リストの場合は実行をスキップする安全策を導入。
  - DB 書込みは冪等性を重視（DELETE→INSERT、ON CONFLICT を期待する jquants_client 側との整合）。

- ルックアヘッドバイアス対策
  - score_news / score_regime / ファクター計算等、すべて target_date パラメータに依存し内部で date.today() を参照しない設計。

- ロギング
  - 各モジュールで適切な debug/info/warning/exception ログを出力（リトライ・フォールバック・データ不足時に詳細ログ）。

Breaking Changes
- なし（0.1.0 が初期リリース想定のため、過去互換性の概念なし）。

Deprecated
- なし。

Removed
- なし。

Acknowledgements / TODO（推定）
- jquants_client / quality モジュールや外部 API との統合部分は別途提供される想定（コード内で import して利用）。
- strategy / execution / monitoring パッケージの具体実装は別途ステージにて提供（現リポジトリはデータ・研究・AI 側の基盤実装に注力）。
- ドキュメントや使用例、ユニットテストの追加により一層の安定化が期待される。

補足
- 本 CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のコミット履歴や PR メッセージがある場合は、それに則った差分の記載を推奨します。