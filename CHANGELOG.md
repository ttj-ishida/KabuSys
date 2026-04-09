CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠し、セマンティックバージョニングに従います。

## [Unreleased]

- 小さな改善・ドキュメント整備、モジュール間の結合をさらに緩めるリファクタなどを予定。
- 監視・実行周り（monitoring / execution）の機能拡張や CLI の追加を検討中。

## [0.1.0] - 2026-04-09

初回リリース。日本株自動売買システム "KabuSys" の基盤的なデータ取得、特徴量・ファクター計算、ニュース NLP（LLM）評価、マーケットカレンダー管理、ETL パイプラインなどを実装。

主な追加点
- 基本パッケージ構成
  - パッケージを公開（kabusys）。__version__ = "0.1.0" を設定。
  - 公開サブパッケージ: data, research, ai, （および strategy, execution, monitoring を __all__ に含めているが各実装は段階的に提供予定）。  

- 設定管理（kabusys.config）
  - .env ファイルおよび OS 環境変数を読み込む自動ローダ実装（プロジェクトルート検出は .git または pyproject.toml を基準）。
  - .env のパース機能を実装（export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ処理、インラインコメント処理）。
  - 自動ロードを KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で無効化可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / Paper Trading 設定 / 監視閾値 / 実行環境等のプロパティを安全に取得。
  - 必須環境変数未設定時は ValueError を送出する _require ヘルパーを追加。
  - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV と LOG_LEVEL の有効値チェックを実装。

- ニュース NLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols を基に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）で各銘柄のセンチメント（-1.0〜1.0）を評価して ai_scores テーブルへ書き込む機能を実装。
  - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）計算ユーティリティ（calc_news_window）。
  - バッチ処理（最大 20 銘柄/回）、1銘柄あたりの最大記事数・文字数制限によるトークン爆発対策。
  - JSON Mode を利用した厳密なレスポンス期待（レスポンスのパース/バリデーション実装）。
  - 429 / ネットワーク断 / タイムアウト / 5xx に対する再試行（指数バックオフ）と、非リトライ系エラー発生時の安全なスキップ。フェイルセーフで未取得銘柄だけを残す設計（部分失敗時に既存スコアを不用意に削除しない）。
  - テストの容易化のため _call_openai_api を差し替え可能に実装。
  - DuckDB の executemany の空リスト制約を考慮した DB 書き込みロジック（DELETE → INSERT の冪等書き込み）。

- マーケットレジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動）200日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull / neutral / bear）を日次判定する機能を実装。
  - DuckDB からの ma200_ratio 計算、raw_news からのマクロキーワードフィルタ取得、OpenAI 呼び出し、スコア合成、market_regime テーブルへの冪等書き込みを実装。
  - API 呼び出しの再試行・フォールバック（API 失敗時は macro_sentiment=0.0）や、内部でのルックアヘッド防止（target_date 未満のみ参照）など設計方針を反映。
  - OpenAI クライアントは OpenAI(api_key=...) を直接生成。テスト時の差し替えを想定。

- データ関連（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分取得・保存・品質チェックの基本フロー（ETLResult データクラスを公開）。
    - backfill（再取得）ロジック、品質チェック問題の収集とエラーフラグ（has_errors / has_quality_errors）。
    - J-Quants クライアント呼び出し（jquants_client 参照）・保存処理を想定した設計。
  - ETLResult を kabusys.data.etl 経由で再エクスポート。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダー（market_calendar）の夜間バッチ更新 job（calendar_update_job）を実装。J-Quants から差分取得して保存するフローを提供。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティを実装。DB 値優先、未登録日は曜日ベースでフォールバック。
    - 保存は冪等設計を想定し、バックフィル（直近数日を再フェッチ）や健全性チェック（極端な future date のスキップ）を実装。
    - DuckDB の日付型変換ユーティリティやテーブル存在チェックを実装。

- リサーチ（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算を実装（prices_daily / raw_financials 参照）。
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（データ不足時の None 処理）。
    - calc_volatility: 20日 ATR、相対 ATR、平均売買代金、出来高比率。
    - calc_value: PER / ROE（最新財務データの取得ロジック込み）。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、rank、統計サマリー（factor_summary）を提供。
  - 依存軽量化方針: pandas 等に依存せず標準ライブラリ + DuckDB SQL を活用。

設計上の重要なポイント（リリースノート）
- ルックアヘッドバイアス回避: 日付関連処理（score_news / score_regime / 各種計算）は内部で datetime.today() や date.today() を直接参照しない。必ず caller が target_date を注入する設計。
- 冪等性と部分失敗耐性: DB 書き込みは DELETE → INSERT 等で置換し、部分失敗時に既存データを不必要に消さないように配慮。
- OpenAI 呼び出しの堅牢化: JSON Mode（response_format）を利用し、429/ネットワーク/タイムアウト/5xx に対する指数バックオフ再試行を実装。応答のパース失敗は警告ログでフォールバック（0.0 やスキップ）する。
- テストしやすさ: _call_openai_api 等をモック差し替えする設計コメントを配置。
- DuckDB 互換性配慮: executemany に空リストを渡せない制約等を考慮したコード（空チェックなど）を実装。

既知の注意点 / マイグレーション
- OpenAI API キーは api_key 引数経由か環境変数 OPENAI_API_KEY で供給する必要あり。未設定時は ValueError を送出する箇所がある。
- .env の自動ロードはプロジェクトルートを .git または pyproject.toml から探索するため、配布環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を用いると自動ロードを抑制できる。
- __all__ に strategy, execution, monitoring が含まれていますが、該当モジュールの完全実装は今後のリリースで提供予定。現バージョンでは data / research / ai 周りが主要実装。

破壊的変更
- 初回リリースのため破壊的変更は無し。

セキュリティ
- 本バージョンではセキュリティ脆弱性は特記なし。API キー・機密情報は環境変数で管理することを推奨。

---

本 CHANGELOG はコードベースの実装内容から推測して作成しています。実際のコミット履歴に基づく正確な変更履歴が必要な場合は Git のログ等を参照してください。