CHANGELOG
=========

すべての重要な変更は「Keep a Changelog」フォーマットに従って記載します。
このファイルは人間にも機械にも読みやすい変更履歴を目的としています。

[Unreleased]
------------

- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-29
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本モジュール群を追加。
  - パッケージのバージョン: 0.1.0 (src/kabusys/__init__.py)
  - 公開サブパッケージ: data, strategy, execution, monitoring（__all__ にて宣言）

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env, .env.local の自動ロード機能を追加（プロジェクトルート検出は .git または pyproject.toml を参照）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env 解析は以下をサポート:
    - export KEY=VAL 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント判定（クォート有無での挙動差異）。
  - 環境変数取得ユーティリティ _require と Settings クラスを提供。
  - Settings は J-Quants トークン、kabu ステーション設定、Slack トークン・チャンネル、DB パス（DuckDB/SQLite）、実行環境 (development/paper_trading/live)、ログレベルの検証を含む。

- AI ニュース NLP (src/kabusys/ai/news_nlp.py)
  - raw_news / news_symbols を集約して OpenAI (gpt-4o-mini) で銘柄ごとのセンチメント（ai_score）を算出して ai_scores テーブルへ書き込む score_news API を実装。
  - ニュース収集ウィンドウ（JST 前日15:00〜当日08:30）を calc_news_window で算出。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄）・記事数/文字数制限・JSON Mode 応答検証・スコア ±1.0 クリップ。
  - リトライ戦略（429・ネットワーク・タイムアウト・5xx に対する指数バックオフ）を実装。
  - レスポンスバリデーションを厳密に行い、不正レスポンス時は該当チャンクをスキップ（フェイルセーフ）。
  - テスト容易性のため OpenAI 呼び出しポイントを内部関数 _call_openai_api として分離（モック可能）。

- 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
  - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して市場レジーム（bull/neutral/bear）を判定する score_regime を実装。
  - MA200 計算は target_date 未満のデータのみを使用してルックアヘッドバイアスを防止。
  - マクロニュース抽出、OpenAI 呼び出し、再試行、エラーフォールバック（失敗時 macro_sentiment=0.0）を実装。
  - 最終結果は market_regime テーブルへ冪等的に書き込み（BEGIN / DELETE / INSERT / COMMIT）し、DB 書込失敗時は ROLLBACK を試行。

- データ処理・ETL (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
  - ETLResult dataclass を導入（ETLの実行結果・計測値・品質問題・エラーの集約）。
  - 差分取得、バックフィル戦略、品質チェックの概念を実装（設計に基づく）。
  - etl モジュールで pipeline.ETLResult を公開再エクスポート。

- マーケットカレンダー管理 (src/kabusys/data/calendar_management.py)
  - market_calendar テーブルを用いた営業日判定 API を提供:
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - DB 登録を優先し、未登録日は曜日ベース（平日）でフォールバックする一貫性あるロジックを採用。
  - カレンダー更新バッチ calendar_update_job を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック）。
  - 最大探索範囲やバックフィル、サニティチェック等の安全策を導入。

- リサーチ（ファクター計算・特徴量探索） (src/kabusys/research/)
  - factor_research.py:
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev を計算（DuckDB SQL ベース）。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算。
    - すべて prices_daily / raw_financials のみ参照、外部発注や API 呼び出しは行わない。
  - feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装（欠損や ties 対応）。
    - rank, factor_summary: ランク変換・統計サマリー（count/mean/std/min/max/median）を提供。
  - research パッケージで主要関数を __all__ 経由で公開。

- DuckDB 実装上の互換性考慮
  - executemany に空リストを渡せない DuckDB の制約に合わせた防御的実装（空チェック）。
  - DuckDB から返る日付のハンドリングユーティリティを追加。

- テスト・運用性
  - OpenAI 呼び出しを差し替え可能にしてユニットテストでモック化可能（news_nlp._call_openai_api, regime_detector._call_openai_api）。
  - ログ出力（logger）を各モジュールに導入し異常時のトレースを容易化。
  - フェイルセーフ設計: API エラーやデータ不足時は例外を全面的に投げず、可能な限り安全側のデフォルト値（例: 中立スコア 0.0 / ma200_ratio=1.0）で継続。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Deprecated
- なし。

Removed
- なし。

Security
- 特に認証やシークレットの保存は環境変数経由を想定（.env ファイル読み込みはローカル運用用）。公開リポジトリに秘密情報を含めないことを推奨。

Notes / 補足
- バージョン 0.1.0 は基盤機能（データ取得・カレンダー管理・ファクター計算・ニュース NLP・レジーム判定）に重点を置いた初期実装です。
- 今後のリリースでの想定追加事項:
  - strategy / execution / monitoring の具体的な実装（発注ロジック、監視、バックテスト基盤等）
  - API クライアント抽象化、より多様なモデルやバックエンド対応
  - 性能チューニング・並列化・詳細な品質チェックルールの強化

Contact
- バグ報告・機能要望はリポジトリの issue にお願いします。