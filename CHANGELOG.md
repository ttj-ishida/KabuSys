# Changelog

すべての notable な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従い、SemVer を採用します。

※注: 本 CHANGELOG はソースコードからの推測に基づいて作成しています。実際のリリースノート作成時はコミットログやリリース担当者による確認を行ってください。

現在のバージョン: 0.1.0

Unreleased
----------
- なし（初回リリース準備）

[0.1.0] - 2026-03-29
-------------------
初回公開リリース。

Added
- 基本パッケージ基盤
  - パッケージルート: kabusys パッケージを導入し、__version__ = "0.1.0" を設定。
  - パブリックサブパッケージを __all__ にて公開: data, strategy, execution, monitoring。

- 環境変数・設定管理 (kabusys.config)
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装。  
    - プロジェクトルートの自動検出 (.git または pyproject.toml を起点) により、CWD に依存しない自動ロードを実現。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
  - .env パーサー実装:
    - コメント行、export KEY=val 形式、クォート内バックスラッシュエスケープ、行内コメントの扱い等に対応。
  - 環境変数読み込み時の上書き制御:
    - override フラグ、protected キーセットにより OS 環境変数を保護して上書き制御。
  - Settings クラスを提供し、アプリケーション設定をプロパティで取得可能:
    - J-Quants / kabuステーション / Slack / DB パス / 環境種別（development/paper_trading/live） / ログレベル等。
    - KABUSYS_ENV / LOG_LEVEL の値検証を実装（不正値では ValueError を送出）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- ニュース NLP（AI）モジュール (kabusys.ai.news_nlp)
  - raw_news, news_symbols を集約して銘柄ごとのニューステキストを生成。
  - OpenAI (gpt-4o-mini) を用いたバッチセンチメント評価を実装:
    - バッチサイズ、1銘柄あたりの最大記事数、最大文字数などの制約を導入してトークン肥大化を抑制。
    - JSON Mode を利用し、厳密な JSON 出力を期待するプロンプト設計。
  - 再試行・バックオフ戦略:
    - 429、ネットワーク断、タイムアウト、5xx に対して指数バックオフのリトライ実装。
    - その他のエラーはスキップして処理継続（フェイルセーフ）。
  - レスポンスの厳密なバリデーションとパース耐性:
    - JSON パース失敗時に外側の最初・最後の {} を抽出して復元する試みを行う。
    - results 配列・code・score の型チェック・未知コード無視・数値の有限性チェック。
    - スコアは ±1.0 にクリップ。
  - DuckDB への書き込みは部分置換（対象コードだけ DELETE → INSERT）を採用し、部分失敗時に既存スコアを保護。
  - 公開 API: score_news(conn, target_date, api_key=None) — 指定日のニューススコアを ai_scores テーブルに書き込む。
  - テスト容易性: _call_openai_api をモック差し替え可能（unittest.mock.patch）。

- 市場レジーム判定モジュール (kabusys.ai.regime_detector)
  - ETF(1321) の 200 日移動平均乖離 (ma200_ratio) とマクロニュース（LLM によるセンチメント）を重み付け合成して市場レジーム（bull/neutral/bear）を日次判定。
  - マクロニュース抽出はマクロキーワードリストに基づいて raw_news を検索。
  - OpenAI (gpt-4o-mini, JSON Mode) を用いた macro_sentiment 評価を実装。API 失敗時は 0.0 をフォールバック。
  - 再試行・バックスオフロジックと 5xx 区別によるリトライ方針を実装。
  - 結果は market_regime テーブルに冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）される。
  - 公開 API: score_regime(conn, target_date, api_key=None) — レジームスコアを計算して保存。

- データ基盤（Data）モジュール
  - カレンダー管理 (kabusys.data.calendar_management)
    - market_calendar テーブルを用いた営業日判定ロジックを提供:
      - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days。
    - DB 登録あり → DB 優先、未登録日は曜日ベースのフォールバック（週末除外）により一貫した振る舞い。
    - カレンダー夜間バッチ calendar_update_job を実装（J-Quants API から差分取得して保存、バックフィル、健全性チェック）。
    - 最大探索日数制限 (_MAX_SEARCH_DAYS) により無限ループ防止。
  - ETL パイプライン (kabusys.data.pipeline, kabusys.data.etl)
    - ETLResult dataclass を導入し、ETL 実行結果（取得数・保存数・品質チェック問題・エラー等）を構造化して返却・ログ化可能に。
    - 差分取得、バックフィル、品質チェックを想定した設計（J-Quants クライアント経由での取得 / save 関数を前提）。
    - DuckDB の互換性を考慮したテーブル存在チェックや最大日付取得ユーティリティを提供。
    - デフォルトのバックフィル日数、カレンダー先読みなどの定数を定義。

- リサーチ / ファクター (kabusys.research)
  - factor_research: モメンタム、ボラティリティ、バリュー等のファクター計算を実装:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（ウィンドウ不足時は None）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新財務を取得して PER / ROE を算出（EPS が 0/欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 各ホライズン（デフォルト 1,5,21 営業日）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（IC）を計算（有効レコード <3 の場合は None）。
    - rank: 同順位は平均ランクで扱うランク付け実装（丸めで ties 対応）。
    - factor_summary: カウント/平均/標準偏差/最小/最大/中央値を返す統計サマリ関数。
  - いずれの関数も DuckDB 接続のみを受け、外部 API へはアクセスしない設計（安全なリサーチ実行）。

Changed
- 設計方針・実装上の注意点を多数文書化:
  - ルックアヘッドバイアス防止のため、datetime.today()/date.today() を直接参照しない設計（target_date を外から渡す）。
  - DuckDB のバージョン互換性（executemany の空リスト回避や日付型取り扱い）に配慮した実装を行った。
  - OpenAI 呼び出し箇所はモジュール間でプライベート関数を共有せず、各モジュールで独立実装（テスト時に差し替えやすい設計）。

Fixed
- フェイルセーフ / ロバストネスの向上:
  - OpenAI API の失敗時に例外を上位へ伝播させずフォールバック（0.0 やスキップ）して処理継続する箇所を導入。
  - DB 書き込み失敗時のトランザクション制御（COMMIT/ROLLBACK と警告ログ）を実装し、ROLLBACK の失敗もログに残すようにした。
  - .env パーサーのエッジケース（クォート内のバックスラッシュ、行内コメント）への対応を追加。

Security
- 明示的なセキュリティ修正は無し。ただし環境変数の上書きガード(protected set) を設け、OS 環境変数を保護する仕組みを導入。

Deprecated
- なし

Removed
- なし

Notes / Implementation details
- OpenAI モデルは gpt-4o-mini を想定し、JSON Mode（response_format={"type": "json_object"}）での利用を前提としたプロンプト設計を行っているため、API レスポンスのパース方法は将来の SDK 変更に対してある程度耐性を持たせている。
- DuckDB を主要な分析 DB として使用。テーブル存在チェックや日付変換ユーティリティを多数実装している。
- テスト容易性のため、外部 API 呼び出し（OpenAI 等）を差し替え可能にしている（内部関数を patch する設計）。
- 実装の多くは「安全に失敗して継続する」方針（フェイルセーフ）で実装されているため、API 一部失敗時でも全体 ETL やスコアリング処理が停止しないようになっている。

今後の予定（提案）
- CI / テストケース用のサンプル DB と fixtures の追加。
- logging の一括設定や structured logging (JSON) の導入。
- ETL 実行の CLI / スケジューラ統合、モニタリング通知（Slack 連携）の実装。