All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠（https://keepachangelog.com/ja/）

[0.1.0] - 2026-03-31
Added
- 初回リリース: kabusys パッケージ（__version__ = 0.1.0）。
- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込み（OS > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途）。
  - .env パーサーの強化:
    - 行頭の "export " プレフィックス対応。
    - シングル/ダブルクォート、バックスラッシュエスケープ対応。
    - インラインコメント判定（クォート無し時は '#' の前が空白/タブならコメント扱い）。
    - 無効行のスキップと読み込み失敗時の警告出力。
  - env 保護機能: OS 環境変数を保護（上書き制御）。
  - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 監視閾値 / 環境・ログレベル判定などのプロパティ）。
  - 環境変数の必須チェック（未設定時は ValueError）。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニュースを作成。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST に対応、UTC 変換）。
    - OpenAI (gpt-4o-mini) を JSON mode で呼び出し、銘柄ごとのセンチメント（-1.0〜1.0）を取得。
    - バッチ処理（最大 20 銘柄/チャンク）、記事・文字数トリム（最大記事数/最大文字数）。
    - リトライ・バックオフ戦略: 429・接続断・タイムアウト・5xx を指数バックオフで再試行。
    - レスポンス検証（JSON 抽出・results リスト・code/score 検証・スコアクリップ）。
    - 書き込み処理は idempotent（DELETE → INSERT、トランザクション、部分失敗時に既存スコアを保護）。
    - テストしやすさ: OpenAI 呼び出しを差し替え可能（_call_openai_api を patch でモック）。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で regime を判定（bull/neutral/bear）。
    - ma200_ratio 計算（target_date 未満のデータのみ使用、データ不足は中立扱い）。
    - マクロキーワードで raw_news をフィルタし、最新記事を LLM に投げて macro_sentiment を取得。
    - OpenAI 呼び出しのリトライ/フェイルセーフ（失敗時 macro_sentiment=0.0）。
    - スコア合成とクリップ、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 成功時 1 を返す。

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum: mom_1m/mom_3m/mom_6m、200日 MA 乖離を計算（データ不足は None）。
    - Volatility / Liquidity: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。
    - Value: raw_financials から最新財務データを取得し PER / ROE を算出（EPS が 0/欠損時は None）。
    - DuckDB 上の SQL + Python による実装、prices_daily / raw_financials のみ参照、外部発注 API には影響なし。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：指定 horizon（デフォルト [1,5,21]）の将来リターンを一括取得。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関でファクター有効性を評価。
    - ランク変換ユーティリティ（rank）：同順位は平均ランク（丸め処理で ties 検出安定化）。
    - 統計サマリー（factor_summary）：count/mean/std/min/max/median を算出。
  - zscore_normalize を data.stats から再エクスポート。

- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルに基づく営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
    - DB 未取得時は曜日ベース（土日を非営業日）でフォールバック。
    - next/prev/get_trading_days は DB 値優先かつ未登録日を曜日フォールバックで補完、一貫性を保持。
    - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新（バックフィル・健全性チェックあり）。
    - 最大探索日数やバックフィル・先読み等の定数で安全性を確保。
  - ETL パイプライン（pipeline）
    - ETLResult データクラスを導入（取得数／保存数／品質問題／エラー情報等を格納）。
    - 差分更新、保存（jquants_client の save_* で idempotent 保存）、品質チェック（quality モジュール）を想定した設計。
    - デフォルトのバックフィル日数、最小データ開始日等の定数を提供。
    - DuckDB のテーブル存在チェックや最大日付取得ユーティリティを実装（ETL 実行支援）。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- 共通実装/設計上の注意点
  - ルックアヘッドバイアス防止のため、各処理で datetime.today()/date.today() を直接参照しない実装方針（target_date を明示的に受ける）。
  - DB 書き込みはトランザクションを用いた冪等処理（BEGIN / DELETE / INSERT / COMMIT）を採用。エラー時は ROLLBACK を試行し警告記録。
  - OpenAI 呼び出しは冪長なリトライ制御とフェイルセーフを組み合わせ、API 障害でも致命的にならないよう配慮。
  - ロギング（各モジュールで logger を利用）や警告出力を多用し障害診断を容易に。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは引数 (api_key) でも環境変数 OPENAI_API_KEY でも指定可能。未設定時は ValueError を送出して明示的に失敗させる設計（安全性向上）。

注記 / 既知の設計判断
- DuckDB のバージョン差異に起因する挙動（list バインドや executemany の空リスト制約）を考慮して実装しているため、運用環境の DuckDB バージョンにより細かな挙動差があり得る点に留意してください。
- OpenAI のレスポンス形式に対して寛容性（前後の余計なテキストの除去や整数で返される code の正規化など）を持たせていますが、プロンプトやモデルの変更時にはバリデーションルールの見直しを推奨します。

お問い合わせ・貢献
- 本 CHANGELOG はコードから推測して作成しています。実装やリリース方針と差異がある場合はご指摘ください。