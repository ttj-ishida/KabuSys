Changelog
=========
すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）に準拠しています。

Unreleased
----------

- （次回リリース用の未リリース項目をここに記載）

0.1.0 - 2026-04-03
------------------

Added
- 初回公開リリース。パッケージ名: kabusys（__version__ = "0.1.0"）。
- パッケージ構成:
  - data, research, ai, execution, monitoring（パブリック API としてエクスポート）。
- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出：.git または pyproject.toml を基準）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント等に対応。
  - 自動ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス / 監視閾値 / 環境（development/paper_trading/live） / ログレベル等のプロパティを取得可能。必須変数未設定時には ValueError を送出。
- データ関連（kabusys.data）
  - カレンダー管理（calendar_management）:
    - market_calendar を元にした営業日判定（is_trading_day）、SQ判定（is_sq_day）、翌前営業日探索（next_trading_day / prev_trading_day）、期間の営業日取得（get_trading_days）を実装。
    - DB 登録がない場合は曜日ベース（土日除外）でフォールバック。
    - 夜間バッチ calendar_update_job を実装（J-Quants クライアント経由で差分取得・冪等保存、バックフィル・健全性チェック付き）。
  - ETL パイプライン基盤（pipeline）:
    - ETLResult データクラス（target_date、取得・保存件数、品質問題、エラー等）。
    - 差分更新・バックフィル・品質チェックを行う設計に基づいたユーティリティ（jquants_client / quality モジュールと連携する想定）。
  - ETL 用ユーティリティ（etl）で ETLResult を公開再エクスポート。
- リサーチ機能（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離などのモメンタム指標を DuckDB SQL で算出。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等のボラティリティ／流動性指標を算出。
    - calc_value: raw_financials から EPS/ROE を取得して PER / ROE を算出（target_date 以前の最新財務データを使用）。
    - 実装は DuckDB 接続を受け取り、prices_daily / raw_financials のみ参照（本番注文 API へはアクセスしない）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。
    - factor_summary: 各ファクターの統計サマリ（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランクで扱うランク関数（丸めによる ties を考慮）。
    - 実装は標準ライブラリ + DuckDB SQL による依存最小化設計。
- AI モジュール（kabusys.ai）
  - news_nlp:
    - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄ごとの ai_score を ai_scores テーブルへ書き込む。
    - ニュースウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST、UTC に変換）を提供（calc_news_window）。
    - バッチサイズ、記事数・文字数上限、JSON レスポンスの検証、スコアの ±1 クリップ、部分成功時の DB 置換（DELETE → INSERT）等を実装。
    - API 呼び出しはリトライ（429/ネットワーク/5xx/タイムアウト）を指数バックオフで行い、失敗・パースエラーはその銘柄チャンクをスキップ（フェイルセーフ）。
  - regime_detector:
    - score_regime: ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - マクロ記事絞り込み（キーワードリスト）、OpenAI 呼び出し（独立実装）、リトライ・フェイルセーフ処理、DB トランザクション（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - API 不通時は macro_sentiment=0 として継続。
- DuckDB 互換性に配慮した実装
  - executemany に空パラメータを渡さない安全対策を実装（DuckDB 0.10 の制約に対応）。
  - DuckDB からの date 値処理や NULL ハンドリングを明示的に行うユーティリティを追加。
- ロギングとエラーハンドリング
  - 各モジュールで詳細なログメッセージ（info/warning/debug）を追加し、例外時に ROLLBACK を試行する等の堅牢性を確保。
- ドキュメンテーション（docstrings）
  - 各モジュールに詳細な処理フロー、設計方針、入力/出力、例外仕様をドキュメントコメントとして追加。

Fixed
- DuckDB executemany の空リストバインド回避（score_news / pipeline などで事前チェックを実装）。
- OpenAI API 呼び出し周りでの例外分類と安全なフェイルバック（429/タイムアウト/5xx をリトライ、その他はスキップ）を整備。

Security
- OpenAI API キーは引数で注入可能（テスト容易性）かつ環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出して明示。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能（テストや CI 用）。

Notes / Known limitations
- 本リリースは主にデータ処理・リサーチ・AI スコアリングの基盤実装が中心であり、実際の発注ロジック（execution）や運用監視（monitoring）の具象実装／統合は別途実装を想定しています。
- OpenAI 呼び出しは gpt-4o-mini の JSON Mode を想定しており、レスポンス形式や SDK の変更によりパース周りの修正が必要になる可能性があります。
- DuckDB のバージョン差分（型バインドや LIST パラメータ挙動）に注意。実行環境での互換性確認を推奨します。
- calendar_update_job / ETL パイプラインは外部 J-Quants クライアントとの連携を前提としており、実行には適切な API クレデンシャルとネットワークアクセスが必要です。

Authors
- kabusys 開発チーム（コードベースの docstrings から推測して作成）

Copyright
- See repository license (本 CHANGELOG はコード内容から推測して作成されています)。