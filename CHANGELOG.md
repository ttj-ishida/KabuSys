Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" の仕様に準拠します。

変更履歴
-------

### Unreleased
- （なし）

### 0.1.0 - 2026-03-29
初回公開リリース。

概要
- 日本株自動売買システム「KabuSys」の初期実装を追加。
- コードはモジュール化され、データ取得（ETL）／カレンダー管理／リサーチ／AIベースのニュース解析と市場レジーム判定などを含む。

Added
- パッケージエントリポイント
  - src/kabusys/__init__.py: パッケージ名、バージョン（0.1.0）および主要サブモジュールの公開（data, strategy, execution, monitoring）。
- 設定管理
  - src/kabusys/config.py:
    - .env ファイルと環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート検出：.git または pyproject.toml）。
    - .env と .env.local の優先順位処理、OS 環境変数の保護機能（protected set）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
    - .env パースの堅牢化（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、コメント処理）。
    - Settings クラスで各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* など）とデフォルト値（KABU_API_BASE_URL, DB パス等）を提供。
    - 環境名（KABUSYS_ENV）とログレベル（LOG_LEVEL）のバリデーション。
- AI モジュール
  - src/kabusys/ai/news_nlp.py:
    - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメント（ai_score）を算出して ai_scores テーブルへ保存する score_news 関数を実装。
    - タイムウィンドウ（JST 前日15:00～当日08:30 に対応する UTC 時間）計算ユーティリティ calc_news_window を追加。
    - バッチ送信（最大 _BATCH_SIZE=20 銘柄）、1銘柄当たり記事数/文字数制限、JSON Mode のレスポンス検証とクリッピング（±1.0）。
    - 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでのリトライを実装。失敗時は該当チャンクをスキップし、他の銘柄は保護する設計。
    - テスト用に API 呼び出し箇所を差し替え可能な実装（_call_openai_api を patch 可能）。
    - DuckDB への書き込みは冪等性を考慮（DELETE → INSERT、executemany の空リスト回避）。
  - src/kabusys/ai/regime_detector.py:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来のマクロセンチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する score_regime を実装。
    - マクロニュース抽出（キーワードリスト）→ OpenAI 呼び出し→ 合成スコア化の一連処理を含む。
    - API エラー時は macro_sentiment=0.0 でフォールバックし、フェイルセーフを確保。
    - DB 書き込みは BEGIN/DELETE/INSERT/COMMIT による冪等処理。失敗時は ROLLBACK を試行して例外を再送出。
- Research（因子・特徴量）
  - src/kabusys/research/factor_research.py:
    - モメンタム（1M/3M/6M リターン、ma200乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER、ROE）の計算関数 calc_momentum / calc_volatility / calc_value を実装。
    - DuckDB を用いた SQL ベースでの計算。データ不足時の None ハンドリング。
  - src/kabusys/research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns、horizons の検証）、IC（スピアマンのρ）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリー（factor_summary）を実装。
    - Pandas 等に依存せず標準ライブラリのみで実装。重複・ties の扱いに配慮したランク付け。
  - src/kabusys/research/__init__.py: 主要関数の再エクスポートを追加。
- Data（データ基盤）
  - src/kabusys/data/calendar_management.py:
    - JPX カレンダーの管理・夜間更新ジョブ（calendar_update_job）と営業日判定ユーティリティ（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - market_calendar テーブルがない場合は曜日ベース（週末は非営業日）でフォールバックする一貫したロジック。
    - lookahead / backfill / sanity チェック（_CALENDAR_LOOKAHEAD_DAYS, _BACKFILL_DAYS, _SANITY_MAX_FUTURE_DAYS）。
  - src/kabusys/data/pipeline.py:
    - ETL パイプライン設計に基づくユーティリティ。差分取得、保存（jquants_client の save_* を使用）と品質チェックを想定。
    - ETLResult dataclass を実装（target_date / fetched/saved counts / quality_issues / errors 等）および to_dict。
    - DuckDB テーブル存在確認や最大日付取得のユーティリティを実装。
  - src/kabusys/data/etl.py: ETLResult の再エクスポートを追加。
  - 各所で jquants_client（jquants API クライアント）との連携を想定（fetch/save の呼び出し箇所を準備）。
- その他
  - テストしやすさを考慮して OpenAI 呼び出し関数をモジュール内で分離（patch 可能）。
  - ロギングによる詳細メッセージと警告の追加（データ不足、APIパース失敗、ROLLBACK 失敗など）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 実装上の設計判断・制約
- ルックアヘッドバイアス対策:
  - datetime.today() / date.today() を内部処理の基準に直接参照しない設計。すべて呼び出し側が target_date を渡す方式。
  - prices_daily クエリは target_date を排他条件にする（date < target_date など）ことで将来データ参照を回避。
- フェイルセーフ:
  - OpenAI API の失敗時は例外ではなくフォールバック（例えば macro_sentiment=0.0）や該当チャンクのスキップを行い、システム全体の停止を避ける方針。
- DuckDB 特性対応:
  - executemany に空配列を渡すとエラーになるバージョンがあるため、空チェックを行ってから実行。
- セキュリティ/運用:
  - 必須環境変数未設定時は明示的に ValueError を投げる（API キー等）。
  - .env 自動ロードはプロジェクトルートを基準に行い、配布後の動作を想定して cwd に依存しない探索を行う。
- テスト容易性:
  - OpenAI 呼び出しを差し替えられるよう内部関数を用意（unittest.mock.patch を想定）。

Security
- （現時点で公開すべきセキュリティ修正はなし）

謝辞
- このリリースはデータ取得・ETL・因子計算・AIベースのニュース解析・市場レジーム判定の初期統合を目的としており、今後の改善（追加のファクター、戦略モジュール、実取引エンジンとの統合、より詳細な品質チェック等）を予定しています。