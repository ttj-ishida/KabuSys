CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-04-04
-------------------

初回公開リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。以下はソースコードから推測できる主要な追加・設計方針・品質改善点の要約です。

Added
- パッケージ基盤
  - kabusys パッケージを公開。モジュール群（data, research, ai, monitoring, strategy, execution など）を __all__ でエクスポートする初期構造を提供。
  - バージョン情報を __version__ = "0.1.0" に設定。

- 設定管理
  - 環境変数・設定読み込みモジュールを実装（kabusys.config）。
  - プロジェクトルート判定ロジックを実装し、.env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可）。
  - .env パーサを独自実装（export プレフィックス、シングル/ダブルクォート、エスケープ、行末コメントの扱いを考慮）。
  - Settings クラスを提供し、J-Quants / kabu API / LINE API / DB パス / 監視閾値 / 実行環境判定（development/paper_trading/live）などのプロパティを型付きで公開。未設定必須値は _require() で明示的なエラーを発生させる。

- ニュース NLP（AI）機能
  - news_nlp.score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を使って銘柄ごとのセンチメント（ai_scores）を生成・書き込みする処理を実装。
    - JSTベースの収集ウィンドウ計算（前日15:00〜当日08:30）を calc_news_window で提供（UTC 換算して DB と比較）。
    - 1銘柄あたり記事数・文字数の上限（トリム）を実装し、最大バッチサイズで API に送信。
    - JSON Mode のレスポンスのバリデーション、スコアの ±1.0 クリップ。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ。失敗時は該当チャンクをスキップして継続するフェイルセーフ設計。
    - テスト容易性のため、_call_openai_api を patch して差し替え可能。
    - DB 書き込みは idempotent（DELETE → INSERT）かつ部分失敗に対して既存データを保護する戦略を採用。

  - regime_detector.score_regime: ETF（1321）の200日MA乖離（重み70%）とマクロニュースのLLMセンチメント（重み30%）を合成し、市場レジーム（bull/neutral/bear）を market_regime テーブルへ冪等書き込みする処理を実装。
    - MA 計算は target_date 未満のデータのみ使用してルックアヘッドバイアスを防止。
    - マクロ記事抽出（キーワードベース）、OpenAI 呼び出し、再試行ロジック、API失敗時のフェイルセーフ（macro_sentiment=0）を実装。
    - OpenAI API に関するエラー分類（429/接続/タイムアウト/5xx と非5xx）に基づく取り扱い。

- データプラットフォーム（Data）
  - ETL パイプラインと結果データ構造（pipeline.ETLResult）を公開。取得数・保存数・品質問題・エラーの集約を行う dataclass を提供。
  - calendar_management モジュールを実装し、市場カレンダー（market_calendar）を用いた営業日判定/次営業日/前営業日/期間内営業日リスト / SQ判定を提供。
    - DB にカレンダーがない場合は曜日ベース（土日休）でのフォールバックを採用。
    - 夜間バッチ calendar_update_job により J-Quants から差分取得→保存する処理を実装。バックフィルと健全性チェックを含む。
  - pipeline モジュール（ETL）設計: 差分取得、idempotent 保存、品質チェック（quality モジュール参照）を行う設計方針を明記。

- リサーチ（研究用）機能
  - research モジュール提供。factor_research（calc_momentum, calc_value, calc_volatility）や feature_exploration（calc_forward_returns, calc_ic, factor_summary, rank）を実装。
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離を計算（データ不足時は None）。
    - calc_volatility: 20日ATR、相対ATR、20日平均売買代金、出来高比率を計算（データ不足時は None）。
    - calc_value: raw_financials から最新財務を取得して PER/ROE を計算。
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを一括で取得。
    - calc_ic: スピアマンランク相関（IC）を実装（3件未満で None）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を実装。
    - rank: 同順位の平均ランク（ties の平均順位）を計算するユーティリティ。

- ロギング・堅牢性
  - 各処理で詳細な logger 呼び出しを追加（info/debug/warning/exception）。トランザクション失敗時の ROLLBACK 試行とログ出力、API エラー時の挙動明示など堅牢性を意識。
  - DuckDB を主要なデータストアとして使用。DB 書き込みは可能な限り冪等化（削除→挿入、ON CONFLICT 方針等）している。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは明示的に引数で渡すか環境変数 OPENAI_API_KEY を使用。未設定時は ValueError を発生させることで誤動作を防止。
- 自動 .env 読み込み時に OS 環境変数を保護するため protected セットを用いた上書き制御を実装。

Notes / 設計上の重要ポイント
- ルックアヘッドバイアス防止: 解析モジュール（news_nlp、regime_detector、research）は datetime.today()/date.today() を内部で参照せず、必ず外部から与えられる target_date（テスト容易性と再現性）を使用するよう設計されています。
- テストのしやすさ: OpenAI 呼び出し部分は内部の _call_openai_api を patch できるようになっており、統合テストでのモック差し替えが容易です。
- フェイルセーフ: 外部API障害時は処理を継続する（デフォルトスコア0や該当チャンクスキップ）方針を採用し、部分失敗が全体停止に繋がらないように設計されています。
- DuckDB 互換性留意: executemany に空リストを渡さない、list 型バインドの回避など DuckDB のバージョン特有実装に配慮しています。

今後の改善案（示唆）
- ai_score / regime 推定の詳細な検証ロジックとユニットテストの充実。
- J-Quants / kabu API クライアント（jquants_client 等）のモック実装・インターフェース安定化。
- リソース監視・監視アラート送信（LINE 等）などの運用周りの実装拡充。
- ドキュメント（API 仕様、運用手順、テストケース）の追加。

--- 

（注）上記は提供されたソースコードの内容・ドキュメント文字列から推測してまとめた変更履歴です。実際のコミット履歴・差分に基づくものではありません。