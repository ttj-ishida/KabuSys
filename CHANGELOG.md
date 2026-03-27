Keep a Changelog
================

全ての重要な変更はこのファイルで管理します。  
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-27
--------------------

Added
- 初回リリース: kabusys パッケージを追加。
  - パッケージ公開情報:
    - バージョン: 0.1.0
    - パッケージトップでの公開モジュール: data, strategy, execution, monitoring
- 環境設定・ロード機能 (kabusys.config)
  - .env および .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサー実装:
    - export プレフィックス対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの扱い（クォート有無に応じた判定）
  - 環境設定ラッパー Settings を実装（J-Quants / kabuステーション / Slack / DBパス / 実行環境 / ログレベル 等のプロパティを提供）。必須環境変数未設定時は ValueError を送出。
- データ（Data）関連
  - ETL フレームワーク（kabusys.data.pipeline）
    - 差分取得・保存・品質チェックの処理方針を実装。
    - ETLResult データクラスを公開（結果集約・品質エラー判定・辞書化ユーティリティ含む）。
    - DuckDB を想定したテーブル存在チェック、最大日付取得ユーティリティ等を実装。
    - 初期データ取得のための最小日付やバックフィル期間等の定数を定義。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPXカレンダーの夜間バッチ更新 job (calendar_update_job) を実装。J-Quants クライアント経由で差分取得 → 冪等保存（ON CONFLICT を想定）。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。DB データがない場合は曜日ベースでフォールバックする一貫した挙動を採用。
    - 最大探索日数やバックフィル日数、健全性チェック等の安全装置を実装。
  - ETL 用の jquants_client / quality モジュールとの連携インターフェースを確立（fetch/save を想定）。
- AI（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約し、銘柄ごとに OpenAI （gpt-4o-mini）でセンチメントスコアを取得して ai_scores テーブルへ保存する処理を実装。
    - 時間ウィンドウ計算ユーティリティ calc_news_window を実装（JST を基準に UTC naive datetime を返す）。
    - バッチ処理（最大 20 銘柄／リクエスト）、1 銘柄あたりの最大記事数・最大文字数トリム、JSON Mode（厳密 JSON）を利用。
    - リトライ設計: 429（レート制限）、ネットワーク断、タイムアウト、5xx を対象に指数バックオフで再試行。その他エラーはスキップして継続（フェイルセーフ）。
    - レスポンスバリデーション: JSON の抽出・検証・スコアクリップ（±1.0）。部分書き換え（対象コードのみ DELETE → INSERT）により部分失敗時に既存データを保護。
    - DuckDB の executemany に対する互換性（空リスト回避）の考慮。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定して market_regime テーブルへ書き込む機能を実装。
    - マクロニュース抽出（キーワードベース）、OpenAI 呼び出し（gpt-4o-mini）およびリトライロジック、API失敗時のフォールバック（0.0）を実装。
    - ルックアヘッドバイアス対策: datetime.today()/date.today() を参照しないクエリ設計（target_date 未満のデータのみ使用）。
    - 冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
- 研究（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム（1M/3M/6M リターン）、200日移動平均乖離、ATR/流動性/出来高指標、バリュー（PER, ROE）などの計算機能を実装。
    - DuckDB を用いた SQL ベースの計算を採用。データ不足時の None 戻し等の安全処理を実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ランク変換、統計サマリー（factor_summary）等を実装。外部ライブラリに依存しない純粋 Python 実装。
  - 研究用ユーティリティのエクスポートを実装（__all__ による公開）。
- ロギングとエラーハンドリング
  - 各モジュールで詳細な info/debug/warning ログを出力するように実装。API 呼び出し失敗時は例外伝播ではなくログ記録＋フォールバックを行う箇所を多く採用し、運用上の堅牢性を高めた。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）
  - ただし実装上、DuckDB executemany の空リスト問題や API レスポンスパース失敗のフォールバック等、既知の運用問題に対する対策を盛り込んでいる。

Security
- 必須の機密情報（OpenAI / Slack / kabu API / J-Quants トークン等）は Settings 経由で取得し、未設定時は明示的にエラーを出すことで運用時の誤設定を早期に検出可能にした。

Notes / Design Decisions
- ルックアヘッドバイアス防止: ほとんどの分析・スコアリング関数は内部で現在時刻を参照せず、引数の target_date に依存する実装とした。
- フェイルセーフ: OpenAI や外部 API の一時エラーはリトライ・ログ・中立値フォールバック等で全体処理を継続する設計。
- DuckDB 前提の実装: SQL を多用し、パフォーマンスと再現性を重視（ただし DB が存在しない場合のフォールバックロジックも用意）。

---

今後の予定（例）
- strategy / execution / monitoring の具象実装追加（発注ロジック・監視・Slack 通知など）
- テストカバレッジ拡充と CI 統合
- jquants_client の実運用テストおよびカレンダー差分取得の堅牢化

（この CHANGELOG はコード内のドキュメンテーションと実装から推測して作成しています。実際のリリースノート作成時にはコミット履歴やリリース方針に基づく追記を推奨します。）