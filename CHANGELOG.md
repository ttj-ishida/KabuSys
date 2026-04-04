# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-04-04

初回リリース。本リリースで導入された主要機能と設計方針の要約を以下に示します。

### Added
- パッケージ構成
  - kabusys パッケージを追加。サブモジュールとして data, research, ai, config 等を含む。
  - パッケージバージョンを src/kabusys/__init__.py にて `__version__ = "0.1.0"` として定義。

- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルート判定は .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env のパースは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（スペース前の # をコメントと認識）に対応。
  - Settings クラスを提供し、アプリケーション設定をプロパティで取得可能（J-Quants / kabu API / LINE トークン / DB パス / 監視設定 / システム設定など）。
  - 必須設定未指定時の明確なエラー (_require) と、環境値の検証（KABUSYS_ENV, LOG_LEVEL）を実装。
  - 環境変数の上書き制御（override/protected）をサポート。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols を集約し、銘柄ごとに OpenAI（gpt-4o-mini）の JSON Mode でセンチメントを算出して ai_scores テーブルへ保存する機能を実装。
    - タイムウィンドウ定義（前日15:00 JST～当日08:30 JST）を calc_news_window で提供。
    - バッチ処理（1 API 呼び出しあたり最大 20 銘柄）、記事数・文字数のトリム、JSON レスポンスの厳密検証、スコア ±1.0 でクリップなどを実装。
    - ネットワーク/429/タイムアウト/5xx に対する指数バックオフリトライと、失敗時のフェイルセーフ（部分成功を保護するための部分書き換え戦略）を実装。
    - API キーは引数注入または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError を送出。
    - テスト性を考慮し、内部の _call_openai_api を patch 可能な実装にしている。
    - パブリック API: score_news(conn, target_date, api_key=None) — 書き込んだ銘柄数を返す。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等的に保存する機能を実装。
    - マクロニュース抽出に使うキーワード群を定義し、取得記事があれば gpt-4o-mini により JSON レスポンス（{"macro_sentiment": ...}）を期待して評価。
    - LLM 呼び出し時のリトライ、サーバーエラー判定、JSON パース失敗時のフォールバック（macro_sentiment=0.0）などの堅牢性を確保。
    - API キーは引数または環境変数 OPENAI_API_KEY から解決。未設定時は ValueError。
    - パブリック API: score_regime(conn, target_date, api_key=None) — 成功時 1 を返す。

- データ処理基盤（src/kabusys/data）
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETL 結果を表す ETLResult データクラスを実装（取得数、保存数、品質検査結果、発生エラー等を集約）。
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client, quality モジュールと連携）。
    - ETLResult.to_dict() によりログ兼監査用の辞書化を可能に。
  - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
    - market_calendar テーブルを用いた営業日判定 API（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）を実装。
    - DB にカレンダーがない場合や未登録日は曜日ベースのフォールバック（平日のみ営業日）を使用して一貫性を保つ設計。
    - calendar_update_job により J-Quants から差分取得・バックフィル・保存を実行（健全性チェック付き）。
    - 最大探索日数やバックフィル幅などの安全パラメータを定義して無限ループや異常値を回避。

- リサーチツール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を SQL ウィンドウ関数で計算。
    - calc_volatility: 20 日 ATR, 相対 ATR, 20 日平均売買代金、出来高比率などを計算。
    - calc_value: raw_financials の最新報告を参照して PER, ROE を計算。
    - すべて DuckDB 接続を受け取り prices_daily / raw_financials のみ参照する安全設計。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: ファクターと将来リターン間のスピアマンランク相関（IC）を実装（有効レコードが 3 未満なら None）。
    - rank: 同順位は平均ランクとして取り扱うランク関数を実装（丸めで ties の漏れを防止）。
    - factor_summary: count/mean/std/min/max/median の基本統計を算出。
  - これらを research パッケージの __init__ でエクスポート。

- DuckDB を主要なローカル分析 DB として想定し、各モジュールが DuckDB 接続（DuckDBPyConnection）を受け取る API 設計を採用。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Design / Implementation Notes（設計上の重要ポイント）
- ルックアヘッドバイアス防止のため、日付判定やウィンドウ計算で datetime.today() や date.today() を内部参照しない設計。すべて target_date を明示的に渡す。
- 外部 API 呼び出し（OpenAI / J-Quants）失敗時は例外で即 abort せず、安全なデフォルト（中立スコア 0.0、部分的スキップ）で処理継続する方針を採用。
- DB 書き込みは基本的に冪等性を意識（DELETE → INSERT の置換や ON CONFLICT 相当の想定）。トランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を確保。
- 単体テスト容易化のため、OpenAI 呼び出し部分は内部関数を patch しやすく実装。

### Known limitations / Todos
- jquants_client, quality など外部モジュールの実装（本コードベースには未同梱）との連携を前提としている。
- PBR・配当利回り等のバリュー指標は現バージョンで未実装（calc_value に注記あり）。
- UI/CLI、運用向けの監視・リトライポリシー一元管理は今後の改善対象。

---

今後のリリースではテストカバレッジ、エラーハンドリングの強化、モジュール間のドキュメント整備、追加指標（PBR 等）や実運用（execution）周りの実装を計画しています。