Changelog
=========
すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」規約に準拠します。

なお、本CHANGELOGは提示されたコードベース（KabuSys v0.1.0 相当）から実装内容を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-04
初期リリース。以下の主要機能・モジュールを提供します。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0 を定義（src/kabusys/__init__.py）。
  - 公開モジュール候補: data, strategy, execution, monitoring（__all__ に列挙）。

- 環境設定 / ロード機構（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルートを .git または pyproject.toml から探索して自動で .env / .env.local を読み込む。
    - 読み込み順序: OS環境変数 > .env.local > .env。
    - OS環境変数を保護するための protected キーセットを扱う。
    - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い（クォートあり/なしでの扱いの差分）等に対応。
  - Settings クラスを提供し、アプリケーション設定をプロパティで取得可能:
    - J-Quants / kabuステーション / LINE / DB パス（duckdb/sqlite）/監視設定（PID/KILL フラグ/閾値）/システム環境（env, log_level, is_live 等）を取得。
    - 必須設定未存在時は ValueError を送出（_require）。

- AI モジュール（src/kabusys/ai/*）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - raw_news / news_symbols を元に、銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini、JSON mode）へバッチ送信しセンチメント（-1.0〜1.0）を算出して ai_scores に書き込む。
    - タイムウィンドウ: 前日15:00 JST ～ 当日08:30 JST（内部は UTC naive で扱う）。
    - バッチ処理・トークン肥大対策: 最大銘柄数 / 最大記事数 / 最大文字数でトリム。
    - リトライ戦略: 429（レート制限）・ネットワーク断・タイムアウト・5xx に対して指数バックオフで再試行。
    - レスポンス検証: JSON 抽出・results 配列検証・コード一致チェック・スコアの数値性と有限性チェック。異常時はスキップしフェイルセーフにより処理継続。
    - DuckDB 互換性考慮: executemany に空リストを渡さない等の実装上の注意。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込んだ銘柄数を返す。APIキー未設定時は ValueError。
    - テスト容易性: _call_openai_api を patch できる設計。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定して market_regime に冪等書き込み。
    - マクロニュース抽出はニュースタイトルのキーワードマッチでフィルタ（複数キーワードリスト）し、最大件数を制限して LLM に投げる。
    - LLM 呼び出しは gpt-4o-mini（JSON mode）を利用、再試行・エラーハンドリングを実装。API失敗時は macro_sentiment=0.0 で継続。
    - ルックアヘッドを避ける設計（date 引数ベース、DB クエリは target_date 未満のみ参照）。
    - 公開関数: score_regime(conn, target_date, api_key=None) → 1（成功）を返す。APIキー未設定時は ValueError。

- データ処理（src/kabusys/data/*）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダーの夜間バッチ更新 job（calendar_update_job）を実装（J-Quants API クライアント経由で差分取得→保存）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - DB データが不十分な場合は曜日ベース（土日除外）でフォールバックする一貫した挙動を保持。
    - 最大探索範囲等の安全ガード（_MAX_SEARCH_DAYS, sanity チェック等）を実装。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - 差分更新・保存・品質チェックを想定した ETLResult データクラスを実装（src/kabusys/data/pipeline.py）。
      - ETLResult は取得数/保存数/品質問題/エラー等を保持し to_dict() で辞書化可能。
      - 品質チェックの重大度（error）判定プロパティ等を提供。
    - pipeline モジュールの ETLResult を etl.py で再エクスポート。
    - ETL の設計方針や定数（バックフィル日数、最小データ日など）を定義。

- 研究用機能（src/kabusys/research/*）
  - factor_research（src/kabusys/research/factor_research.py）
    - Momentum（1m/3m/6m リターン、MA200乖離）、Volatility（20日 ATR 等）、Value（PER, ROE）等の計算関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB を用いた SQL ベースの実装。欠損やデータ不足時の扱いを明示。
  - feature_exploration（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク関数（rank）、ファクター統計サマリ（factor_summary）を実装。
    - ランクの同順位処理（平均ランク）やスピアマン相関の計算を自前実装し外部依存を避ける。
  - research パッケージの __init__ で主要関数を再エクスポート。

### Security
- 環境変数読み込み時に OS 環境変数を保護（protected set）し、.env による上書きを制御可能。
- OpenAI API キーは引数で注入可能（api_key）でテストと運用で柔軟に扱える。未設定時は ValueError を発生させ早期に検出。

### Design / Reliability notes (設計上の注記)
- ルックアヘッドバイアス対策: 全ての「日次」処理は datetime.today() / date.today() に依存せず、明示的な target_date を受け取る設計。
- データベース書き込みは冪等性を重視（DELETE→INSERT / BEGIN/COMMIT/ROLLBACK を用いた扱い）。
- OpenAI 呼び出しは JSON mode（response_format）を使用し、レスポンスパースや不正フォーマットに対して寛容にフォールバックする実装。
- テスト容易性を考慮し、外部 API 呼び出し部分（_call_openai_api 等）を patch 可能な形で実装。

### Changed
- 初版のため該当なし。

### Fixed
- 初版のため該当なし。

### Removed / Deprecated
- 初版のため該当なし。

----------

注: 本CHANGELOGは提供されたソースコードから推測してまとめたもので、実際のリポジトリの履歴（コミット・リリースノート）とは異なる場合があります。追加のコミットやモジュール（strategy / execution / monitoring）の実装があればそれに応じて本CHANGELOGを更新してください。