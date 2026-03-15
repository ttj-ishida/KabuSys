# KabuSys

日本株向けの自動売買（アルゴリズムトレーディング）システムの骨組みとなるPythonパッケージです。  
このリポジトリは、データ取得、戦略実装、発注（実行）、監視の4つの責務を分離したシンプルな構成を提供します。

バージョン: 0.1.0

---

## 概要

KabuSysは、日本株自動売買システムの基本構造（フレームワーク）を提供します。具体的な取引ロジックや取引所APIへの接続は含まず、以下のような責務ごとにモジュールを分けて実装を行えるようにしています。

- データの収集・加工（data）
- 売買戦略の定義・評価（strategy）
- 注文の発行・管理（execution）
- 稼働状況の監視・ログ（monitoring）

このプロジェクトは拡張や実装の起点として利用できます。

---

## 機能一覧

- プロジェクト骨組み（パッケージ構成）を提供
- サブモジュールの分離（data, strategy, execution, monitoring）
- パッケージメタ情報（バージョン管理）を提供

注：現状はインフラ（インターフェース・パッケージ構成）を提供する段階で、実際のデータソース接続や注文API連携、具体的戦略ロジックは含まれていません。利用者は各サブパッケージに具体実装を追加します。

---

## 要件

- Python 3.8 以上（推奨）
- 仮想環境の利用を推奨（venv / virtualenv / poetry 等）

必要な外部ライブラリは、実装に応じて追加してください（例：HTTPクライアント、pandas、numpy、取引所用SDK 等）。

---

## セットアップ手順

1. リポジトリをクローンする
   ```
   git clone <リポジトリURL>
   cd <リポジトリ名>
   ```

2. 仮想環境を作成し、有効化する（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell では .venv\Scripts\Activate.ps1)
   ```

3. パッケージをインストールする
   - プロジェクトに pyproject.toml / setup.cfg 等がある場合:
     ```
     pip install -e .
     ```
   - ない場合は開発中は Python のモジュール検索パスに `src` を含めるか、パッケージ化してください。簡易的には実行時にカレントディレクトリから `src` をインポートパスに追加する方法もあります。

4. 依存ライブラリがあれば `pip install <package>` で追加してください。

---

## 使い方（基本例）

インストールまたはパス設定後、Python から以下のように利用します。

- バージョン確認
```python
import kabusys
print(kabusys.__version__)  # 0.1.0
```

- サブパッケージの参照
```python
import kabusys.data as data
import kabusys.strategy as strategy
import kabusys.execution as execution
import kabusys.monitoring as monitoring
```

各サブパッケージの想定役割（実装例のガイド）：

- kabusys.data
  - 市場データや証券情報の取得、前処理（例: CSV / DB / API からの取得）
  - 終値・出来高・ティックデータの整形やインジケーター計算

- kabusys.strategy
  - シグナル生成ロジック（エントリー/エグジット判定）
  - バックテスト用のインターフェース（設計次第で追加）

- kabusys.execution
  - 注文作成・送信・約定確認（取引所API、証券会社APIのラッパ）
  - 注文管理（注文ID管理、キャンセル、リトライ等）

- kabusys.monitoring
  - 稼働状況の監視（ログ、メトリクス、アラート）
  - 実行状態のダッシュボード連携等

簡単な擬似コード例（戦略を実行して注文を出す流れ）：
```python
# 以下はあくまで例示です。実際には各モジュールに具体実装を追加してください。

# データ取得
quotes = data.get_latest_quotes(symbol="7203")  # 例: トヨタ自動車の銘柄コード

# 戦略判定
signal = strategy.generate_signal(quotes)

# 注文実行
if signal == "BUY":
    execution.place_order(symbol="7203", side="BUY", qty=100)
elif signal == "SELL":
    execution.place_order(symbol="7203", side="SELL", qty=100)

# 監視・ログ
monitoring.log_trade(...)
```

---

## ディレクトリ構成

このリポジトリの主要なディレクトリ構成（現状のファイル）:

```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py            # パッケージメタ情報（version, __all__）
│     ├─ data/
│     │  └─ __init__.py         # データ取得・前処理用モジュール（実装を追加）
│     ├─ strategy/
│     │  └─ __init__.py         # 戦略ロジック用モジュール（実装を追加）
│     ├─ execution/
│     │  └─ __init__.py         # 注文実行・API連携用モジュール（実装を追加）
│     └─ monitoring/
│        └─ __init__.py         # 監視・ロギング用モジュール（実装を追加）
└─ README.md
```

---

## 開発 / 拡張のヒント

- 各サブパッケージにインターフェース（抽象基底クラス）を用意し、具体実装を差し替えられる設計にするとテストや実運用で便利です。
- テストを書く（pytest など）習慣を付け、戦略ロジックや発注ロジックはユニットテストでカバーすることを推奨します。
- 実運用ではAPIキー・認証情報は環境変数やVault等の安全な手段で管理してください（ソース管理に含めない）。
- 注文実行部分はサンドボックス環境で十分に検証した後、本番APIを使用してください。

---

## 貢献

バグ報告、機能提案、PR歓迎です。貢献ガイドライン（CONTRIBUTING.md）を用意しておくとスムーズです。

---

## ライセンス

このリポジトリのライセンスは明記されていません。利用・配布する前に適切なライセンスファイル（LICENSE）を追加してください。

---

作成・保守: KabuSys チーム

（注）このREADMEは現状のパッケージ構成に基づいた基本的な説明です。具体的なAPI連携や戦略実装を行う場合は、それらに応じた追加のドキュメントを作成してください。