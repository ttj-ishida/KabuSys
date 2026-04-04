CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記録します。本プロジェクトは Keep a Changelog のガイドラインに従って管理されています。
リリース番号はセマンティックバージョニングに従います。

[Unreleased]
------------

- （現時点のコードベースではバージョン 0.1.0 が定義されています。将来の変更はここに追加してください）

[0.1.0] - 2026-04-04
--------------------

Added
- パッケージの初期リリースを追加。
  - パッケージメタ: kabusys/__init__.py に __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開。

- 環境設定 & 自動 .env ロード機能 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動検出して読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能（テスト用途対応）。
  - .env のパースは export 前置、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントなどに対応する堅牢な実装を採用。
  - 読み込み時の上書き制御（override）と OS 環境変数保護（protected）をサポート。
  - Settings クラスを提供し、J-Quants / kabu API / LINE / DB パス / 監視設定 / システム設定（KABUSYS_ENV, LOG_LEVEL）等のプロパティ経由でアクセス可能。
  - 設定値のバリデーション（env 値の許容集合やログレベルチェック、必須値チェック）を実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（ai_score）を算出。
  - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST 相当（UTC に変換）を対象。calc_news_window を提供。
  - バッチ処理: 最大 20 銘柄ずつ API へ送信し、1 銘柄は複数記事を結合して最大文字数でトリム。
  - 再試行 / バックオフ: 429・ネットワーク切断・タイムアウト・5xx を対象とした指数バックオフ実装。
  - レスポンスの厳密バリデーション（JSON モードでの前後ノイズ除去、results 配列の構造検査、コード照合、スコア数値性検証）。
  - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等的に保存（DELETE → INSERT）。
  - テスト容易性: OpenAI 呼び出しは内部 _call_openai_api を経由し、ユニットテストで差し替え可能。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロセンチメント（30%）を合成して daily market_regime を算出。
  - マクロセンチメントはマクロ系キーワードでフィルタした raw_news のタイトル群を LLM（gpt-4o-mini）へ送り JSON で受け取り。
  - LLM 呼び出し失敗時はフェイルセーフとして macro_sentiment = 0.0 を採用。
  - 計算結果（regime_score, regime_label, ma200_ratio, macro_sentiment）を market_regime テーブルに冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
  - ルックアヘッドバイアス対策: target_date 未満のデータのみ参照、date.today() を直接参照しない設計。
  - OpenAI 呼び出しは独立実装で、news_nlp からの共有関数を用いない（モジュール結合軽減）。

- リサーチ / ファクター & 特徴量解析（kabusys.research）
  - factor_research:
    - モメンタム: mom_1m / mom_3m / mom_6m, ma200_dev を計算する calc_momentum を提供。データ不足時は None を返す。
    - ボラティリティ / 流動性: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算する calc_volatility を提供。必要行数未満は None。
    - バリュー: raw_financials から最新財務を取得して PER / ROE を計算する calc_value を提供（EPS が無効な場合は None）。
    - DuckDB のウィンドウ関数を活用し、営業日ベースのラグ・移動平均を高速に算出。
  - feature_exploration:
    - 将来リターン calc_forward_returns（horizons デフォルト: [1,5,21]）を提供。horizons の検証あり。
    - IC（Information Coefficient）calc_ic：スピアマンランク相関を実装。有効レコードが 3 未満なら None を返す。
    - ランキングユーティリティ rank（同順位の平均ランク処理、丸め処理で ties を安定化）。
    - 統計サマリー factor_summary（count/mean/std/min/max/median）を提供。
  - research/__init__.py で主要関数を再エクスポート。

- データ基盤ユーティリティ（kabusys.data）
  - calendar_management:
    - JPX カレンダーの夜間バッチ更新（calendar_update_job）を実装。J-Quants クライアントを用いて差分取得 → 保存（ON CONFLICT 相当）するワークフロー。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供し、DB が欠落している場合は曜日ベースでフォールバック。
    - 最大探索日数・バックフィル・健全性チェックを実装して安全性を確保。
  - pipeline / etl:
    - ETLResult データクラスを公開（kabusys.data.etl から再エクスポート）。ETL の取得数・保存数・品質問題リスト・エラーリスト等を保持。
    - pipeline.py にて差分更新・保存・品質チェックの設計を実装（J-Quants クライアント経由、バックフィル制御、品質問題の収集方針）。
    - DuckDB の制約（executemany に空リストを渡せない等）への配慮を実装。

Other notes / Implementation decisions
- 全体としてルックアヘッドバイアス防止のため、日付は関数引数 target_date を用いる設計で、datetime.today()/date.today() の直接参照を避ける（ただし calendar_update_job は実行日の取得に date.today() を使用する）。
- OpenAI API 周りはリトライ戦略・エラーハンドリングを念入りに実装。API 失敗時にスコア算出を中止せずフェイルセーフ値で継続する方針。
- テスト容易性のため、API 呼び出し部分は内部関数で分離しており unit test でモック差し替えが可能。
- DuckDB を主要な組込み DB として使用。SQL は互換性とパフォーマンスを考慮してウィンドウ関数や ROW_NUMBER / LEAD / LAG を多用。
- ロギングと警告を多用し、異常やデータ不足時に情報を残す。

Known limitations / TODO（初期リリース時点）
- PBR・配当利回り等の一部バリューファクターは未実装。
- ai モジュールは OpenAI のレスポンス形式に強く依存しており、将来の API 仕様変更に備えた追加対応が必要となる可能性あり。
- calendar_update_job / pipeline の外部依存（J-Quants クライアント）でのネットワーク障害・API 仕様変更に対するフォールバックは限定的。監視・アラート設計が必要。

--- 

ライセンスやリリース手順、パッケージ配布（PyPI 等）に関する情報は別途ドキュメントに記載してください。