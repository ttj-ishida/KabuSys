# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-28
初回リリース。

### Added
- パッケージ骨組み
  - kabusys パッケージ初期実装（__version__ = 0.1.0）。
  - サブパッケージ構成: data, research, ai, execution, strategy, monitoring（__all__ で公開）。

- 設定 / 環境変数管理
  - 自動 .env ロード機能を実装（プロジェクトルートの .git / pyproject.toml を起点に探索）。
  - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）と上書き保護機構を実装。
  - .env 行パーサ：コメント、export プレフィックス、クォート内エスケープ、インラインコメント処理に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト目的）。
  - Settings クラスを導入：J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル等の取得とバリデーション（未設定時は ValueError）。

- データプラットフォーム（data）
  - カレンダー管理（calendar_management）
    - market_calendar を利用した営業日判定 API（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB 登録値優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job：J-Quants API から差分取得し冪等的に保存（バックフィル、健全性チェックを含む）。
  - ETL パイプライン用ユーティリティ（pipeline / etl）
    - ETLResult データクラス（取得数 / 保存数 / 品質問題 / エラー情報等を格納）。
    - 差分取得・バックフィル・品質チェックを想定した設計（id_token 注入可能）。
    - _table_exists / _get_max_date 等の汎用ヘルパを実装。
  - etl モジュールは pipeline.ETLResult を再エクスポート。

- 研究用 / ファクター計算（research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）計算（データ不足時は None）。
    - calc_volatility: 20 日 ATR（atr_20）, atr_pct, 20 日平均売買代金, 出来高比率を計算。
    - calc_value: raw_financials から最新財務データを取得して PER/ROE を計算（EPS 0/欠損は None）。
    - DuckDB を用いた SQL + Python 実装で外部 API へアクセスしない設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。入力検証あり。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効データ不足時は None。
    - rank: 同順位は平均ランクで処理（丸め防止のため round を使用）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを算出。
  - research.__init__ で主要関数を公開。

- AI 関連（ai）
  - news_nlp:
    - score_news: raw_news + news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント（ai_scores）を書き込む。
    - ニュースウィンドウ計算（JST 基準 → UTC 変換）を提供（calc_news_window）。
    - バッチ処理（最大 _BATCH_SIZE=20）、記事トリム（記事数・文字数制限）、レスポンス検証、スコアクリップ（±1.0）。
    - 再試行（429/ネットワーク/タイムアウト/5xx）を指数バックオフで実施。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - レスポンスの堅牢な JSON 復元（余分な前後テキストから最外の {} を抽出）とバリデーション。
    - DuckDB の executemany に対する互換性処理（空リスト回避）と、部分失敗時に既存スコアを保護するための個別 DELETE → INSERT 戦略。
    - テスト用に _call_openai_api を patch 可能。
  - regime_detector:
    - score_regime: ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime に冪等保存。
    - マクロキーワードフィルタで raw_news を抽出し、OpenAI により macro_sentiment を推定（記事がない場合は LLM 呼び出しを行わず 0.0）。
    - API 呼び出し失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - OpenAI 呼び出しは専用実装でモジュール間の結合を避ける（テスト時に差し替え可能）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK のログ処理。

### Fixed / Behavior improvements
- ルックアヘッドバイアス防止
  - datetime.today() / date.today() を内部計算の基準として直接参照しない設計。すべてのスコア/ETL/ウィンドウは明示的な target_date を受け取り、その前後処理は明確に排他条件を使う。
- レジリエンスと互換性
  - OpenAI 呼び出しの失敗ハンドリング（リトライ/フェイルセーフ/ログ出力）を強化。
  - DuckDB のバージョン差異（executemany の空リスト等）に対する互換性処理を追加。
  - market_calendar が未取得・まばらな場合の一貫したフォールバック（曜日ベース）を確立。
- ロギングと警告
  - データ不足やパース失敗、ROLLBACK 失敗等を適切に警告ログで通知。

### Deprecated
- なし

### Removed
- なし

### Security
- なし（公開時点で既知のセキュリティ修正はありません）

---

補足 / 開発メモ:
- OpenAI API の利用箇所はテスト容易性のため _call_openai_api をパッチして差し替え可能です。
- 一部外部モジュール（例: kabusys.data.jquants_client）への依存が存在します。ETL / カレンダー更新は外部 API クライアント実装に依存します。
- 今後のリリースではログの構造化、より詳細な品質チェックルール、ならびに追加ファクターの実装・最適化を予定しています。