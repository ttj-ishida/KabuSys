CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog のガイドラインに従って管理されています。
（https://keepachangelog.com/ja/）

Unreleased
---------

- なし

[0.1.0] - 2026-04-09
--------------------

Added
- 基本パッケージ初期実装を追加（__version__ = 0.1.0）。
- 環境変数 / 設定管理モジュールを追加（kabusys.config）。
  - プロジェクトルートを __file__ を起点に .git または pyproject.toml で自動検出。
  - .env / .env.local を自動ロード（OS 環境変数を保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - export 形式、クォート（シングル／ダブル）やエスケープ、インラインコメントのパースに対応。
  - 必須キー検証関数 (_require)、環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
  - 各種設定プロパティ（J-Quants / kabu API / LINE / DB パス / 監視閾値 / PID・kill フラグ関連）を提供。

- ポートフォリオ構築モジュールを追加（kabusys.portfolio）。
  - 候補選定: select_candidates — スコア降順、同点は signal_rank でタイブレーク。
  - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア加重、全スコア0時は等金額にフォールバックして WARNING ログ）。
  - リスク調整: apply_sector_cap — セクター集中上限をチェックして候補を除外（unknown セクターは無視）。
  - レジーム乗数: calc_regime_multiplier — 'bull'/'neutral'/'bear' マッピング、未知レジームは警告後フォールバック。
  - 株数決定: calc_position_sizes — allocation_method ("risk_based" / "equal" / "score") 対応、
    単元丸め（lot_size）、1銘柄上限 / aggregate cap、コストバッファによる保守的見積もり、
    available_cash に基づくスケールダウン（残差は lot 単位で公平に配分）を実装。

- リサーチ / ファクター計算モジュールを追加（kabusys.research）。
  - Momentum ファクター: calc_momentum — 1M/3M/6M リターン、MA200 乖離（データ不足時は None）。
  - Volatility / Liquidity ファクター: calc_volatility — ATR20, ATR 比率, 20日平均売買代金, 出来高比率（必要行数未満は None）。
  - Value ファクター: calc_value — raw_financials から最新財務を結合して PER / ROE を算出（EPS 0/欠損は None）。
  - 将来リターン計算: calc_forward_returns — 複数ホライズン（デフォルト [1,5,21]）を一括取得、入力検証あり。
  - IC 計算: calc_ic — スピアマンのランク相関（ties 平均ランク処理）、有効レコードが少ない場合は None。
  - 統計サマリー: factor_summary — count/mean/std/min/max/median を計算。
  - ランク関数: rank — 同順位は平均ランク、丸め誤差対策の round(,12) を使用。
  - 実装方針: DuckDB 接続を受け取り prices_daily / raw_financials のみ参照、外部ライブラリに依存しない純粋計算。

- AI 関連モジュールを追加（kabusys.ai）。
  - ニュース NLP（kabusys.ai.news_nlp）:
    - raw_news + news_symbols を銘柄別に集約して OpenAI（gpt-4o-mini）へバッチ送信しセンチメントを算出。
    - バッチサイズ、記事・文字数上限、タイムウィンドウ（前日15:00 JST〜当日08:30 JST を UTC に変換）を実装。
    - API 呼び出しに対して 429/ネットワーク/タイムアウト/5xx を対象に指数バックオフでリトライ、その他エラーはスキップ。
    - レスポンスの厳密バリデーション（JSON 抽出、results フォーマット、コード確認、スコア数値化）を実施。スコアは ±1.0 にクリップ。
    - 書き込みは冪等に DELETE → INSERT（対象コードのみ）で実行。DuckDB executemany の空配列制約に対処。
    - テスト用に _call_openai_api を差し替え可能に設計。
    - 公開 API: score_news(conn, target_date, api_key=None) を提供。

  - レジーム判定（kabusys.ai.regime_detector）:
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して daily regime ('bull'/'neutral'/'bear') を判定。
    - マクロニュース抽出はキーワードベース（複数キーワード）、最大記事数制限あり。記事がない場合は macro_sentiment=0.0（フォールバック）。
    - LLM 呼び出しに対してもリトライとフェイルセーフを実装。レスポンスパース失敗時は 0.0 を採用して継続。
    - スコア合成と閾値判定（BULL/BEAR 閾値）を実装。結果を market_regime テーブルへ冪等書き込み。
    - 公開 API: score_regime(conn, target_date, api_key=None) を提供。

- 監視ログ永続化層を追加（kabusys.monitoring.monitoring_db）。
  - SQLite 用初期化関数 init_monitoring_db(conn) を実装。
  - system_status, trade_logs, positions, risk_logs 等のテーブルおよび関連インデックスを作成（冪等）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Notes / 設計上の重要点
- ルックアヘッドバイアス回避: 日付判定時に datetime.today()/date.today() を直接参照しない設計（target_date を明示的に渡す）。
- フェイルセーフ: 外部 API（OpenAI）失敗時は例外を上位に伝播させずフォールバック値を使って継続する箇所が多数（ニュース NLP・レジーム判定など）。
- テスト容易性: OpenAI 呼び出しやファイル読み込み等を差し替え可能に実装（単体テスト用の patch を想定）。
- DB 操作は冪等に実行（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

今後の予定（想定）
- 銘柄ごとの単元（lot_size）をマスター化して銘柄別対応へ拡張。
- prices のフォールバック価格対応（price が欠損のときの見積り改善）。
- 追加ファクター／ファクター正規化ユーティリティの公開拡充。
- テストカバレッジの拡大と OpenAI 呼び出しのモック強化。

-----------------------------------------------------------------------------