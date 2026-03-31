# Changelog

すべての重要な変更点はこのファイルに記録します。本ファイルは「Keep a Changelog」フォーマットに準拠します。

## [Unreleased]
（現時点の開発中の変更はここに記載します。特になし）

## [0.1.0] - 2026-03-31
初回リリース — 日本株自動売買プラットフォームの基礎モジュール群を実装。

### 追加
- パッケージ初期化
  - kabusys パッケージを公開（__version__ = 0.1.0、公開サブパッケージ: data, strategy, execution, monitoring）。
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（OS 環境変数 > .env.local > .env の優先順位）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサで以下の表記に対応:
    - export KEY=val 形式
    - シングル/ダブルクォート付き値（エスケープ処理対応）
    - コメント（#）の取り扱い（クォート外かつ直前がスペース/タブの場合のみコメントとして扱う）
  - 既存 OS 環境変数を保護する protected キーセットの導入（.env.local は override=True だが protected は上書きしない）。
  - Settings クラスを提供し、各種設定をプロパティ経由で取得:
    - J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）/ログレベル検証など。
  - 必須環境変数未設定時は明確な ValueError を送出する _require ヘルパー。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news + news_symbols から銘柄毎にニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ保存する処理を実装。
    - 設定: バッチサイズ、1銘柄あたり最大記事数／文字数、JSON Mode を利用したレスポンス整形。
    - エラー処理: 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ、その他は失敗をログに記録してスキップ（フェイルセーフ）。
    - レスポンスの堅牢なバリデーション（JSON 抽出、"results" リスト検証、コード正規化、スコアの finite チェック、±1.0 クリップ）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
    - calc_news_window ユーティリティ（日本標準時基準のニュース収集ウィンドウ計算）を実装。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動）200日移動平均乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込みする処理を実装。
    - OpenAI 呼び出しは gpt-4o-mini、JSON 出力を期待。API 呼び出し失敗時は macro_sentiment=0.0 にフォールバック。
    - データ不足時は MA 比率を中立（1.0）として扱うなどフォールバック動作を明示。
    - LLM 呼び出しやレスポンスパースの失敗に対してリトライやログ出力を行う堅牢設計。
    - テスト向けに _call_openai_api の差し替えを想定。

- データプラットフォーム（kabusys.data）
  - マーケットカレンダー管理（calendar_management）
    - market_calendar テーブルを利用した営業日判定機能を実装:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB 登録がない場合は曜日ベース（土日除外）のフォールバックを行い、DB がまばらでも一貫性のある判定を返す。
    - calendar_update_job を実装（J-Quants から差分取得 → 冪等保存、バックフィル、健全性チェック）。
  - ETL パイプライン（pipeline）
    - 差分取得 → 保存 → 品質チェック を行う ETL フレームワークの基礎を実装。
    - ETLResult データクラスを導入（取得数／保存数／品質問題／エラーを集約）。to_dict により品質問題の要約を辞書化。
    - テーブル存在確認や最大日付取得などのユーティリティ関数を実装。
    - jquants_client および quality モジュールとの連携想定（API クライアント注入や部分失敗時の保護を考慮）。

- リサーチ（kabusys.research）
  - factor_research：
    - calc_momentum（1M/3M/6M リターン、200日 MA 乖離）、calc_volatility（20日 ATR、相対 ATR、平均売買代金、出来高比率）、calc_value（PER、ROE）を実装。
    - DuckDB を用いた SQL ベースの実装で、データ不足時の None ハンドリングを明示。
  - feature_exploration：
    - calc_forward_returns（任意ホライズンの将来リターンを一括クエリで取得）、calc_ic（スピアマン ρ によるランク相関）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存せず標準ライブラリと DuckDB のみで実装。
  - research パッケージは zscore_normalize を data.stats から再利用できるよう公開。

### 変更（設計上の重要ポイント）
- ルックアヘッドバイアス対策
  - 各 AI / スコアリング / リサーチ機能は内部で datetime.today() / date.today() を直接参照しない設計（呼び出し元が target_date を与えることで過去データのみを参照）。
- DuckDB 互換性
  - executemany に空リストを渡さないなど DuckDB の既知の制約を考慮した実装。
- DB 書き込みは冪等性を意識
  - market_regime / ai_scores などへの書き込みは DELETE → INSERT の形で既存データを置換（BEGIN/COMMIT/ROLLBACK を利用）。
- OpenAI とのやり取りは JSON Mode を利用しつつ、現実的なレスポンス不正（前後に余計なテキストが混ざる等）を補正して堅牢にパースする実装を導入。
- ログ・警告
  - データ不足・API失敗時に詳細な警告ログを出すことで運用時の原因追跡を容易にする。

### 修正（バグフィックス相当・安全策）
- .env 読み込みでのファイル I/O エラー発生時に warnings.warn を発行して処理継続するようにし、クラッシュを防止。
- OpenAI API 呼び出しで 5xx / タイムアウト等のハンドリングを細分化（APIError の status_code 有無を安全に扱う）。
- JSON パース失敗やレスポンス不整合時に例外を投げずフェイルセーフで 0.0 や空辞書にフォールバックする動作を標準化。

### その他
- テスト容易性のため、OpenAI 呼び出し関数をモジュール内で分離しており、unittest.mock.patch による差し替えが可能。
- 多くの関数で logger.debug / logger.info / logger.warning / logger.exception により詳細ログを出力するよう設計。

---

今後の予定（想定）
- strategy / execution / monitoring の具体実装とテストの追加
- jquants_client 実装との統合テスト、ETL スケジューリング周りの運用整備
- ドキュメント（使用例・設定方法・DB スキーマ）および CI テストの拡充

---

以上。もし特定ファイルや変更点を強調してほしい、あるいは別のフォーマット（英語版やリリースノート向け短縮版）を作成したい場合は教えてください。