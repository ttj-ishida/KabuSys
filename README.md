# KabuSys

日本株向け自動売買（アルゴリズムトレーディング）システムの骨組みを提供する Python パッケージです。  
このリポジトリは基本パッケージ構成（データ取得、ストラテジ、注文実行、監視）を備えたテンプレートで、実際の取引ロジックや API 統合を各自で実装して使います。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 設定
- 使い方（簡単な例）
- 開発／拡張ガイド
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株の自動売買を行うための骨組みを提供するパッケージです。以下の主要コンポーネントを想定しています。

- data: 市場データ取得や履歴データ管理
- strategy: 取引戦略の実装（シグナル生成等）
- execution: 注文送信や約定管理（ブローカー API 統合）
- monitoring: ログ、アラート、ダッシュボード等の監視機能

現状はモジュールの雛形があるのみで、各モジュールの中身はプロジェクト固有の要件に応じて実装してください。

---

## 機能一覧
- プロジェクト骨組み（パッケージ構造）提供
- モジュール分離（データ取得・戦略・実行・監視）
- 拡張しやすいテンプレート設計

（注）実際の市場データ取得や注文送信、リスク管理、ログ記録などの具体実装は含まれていません。各自で実装または専用ライブラリ／API を統合してください。

---

## 前提条件
- Python 3.8 以上を推奨
- 仮想環境の利用を推奨（venv、virtualenv、poetry 等）
- 取引 API（kabuステーション、証券会社 API 等）を使用する場合は、その API のクレデンシャルや SDK が必要

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <このリポジトリの URL>
   cd <リポジトリのディレクトリ>
   ```

2. 仮想環境の作成（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージのインストール  
   現状 requirements.txt は含まれていません。必要なパッケージ（requests、pandas、websocket-client など）をプロジェクトに応じて追加してください。例:
   ```
   pip install requests pandas
   ```

4. 開発インストール（オプション）
   パッケージとして扱いたい場合はプロジェクトルートに pyproject.toml もしくは setup.py を用意し、以下でインストールします。
   ```
   pip install -e .
   ```

---

## 設定
API キーや接続情報などの設定は、環境変数または設定ファイル（例: config.yaml、.env）を使うことを推奨します。

例: `.env`
```
KABU_API_KEY=xxxxxxxxxxxxxxxx
KABU_API_SECRET=yyyyyyyyyyyyyyyy
```

安全上の理由から、API キーはリポジトリに含めないでください（.gitignore で除外）。

---

## 使い方（簡単な例）
現状のパッケージはモジュールの雛形のみです。以下は各モジュールに最低限のクラス・インターフェースを追加して使うための例です。

1) import（パッケージ確認）
```python
import kabusys
print(kabusys.__version__)  # 0.1.0
```

2) 推奨されるインターフェース例（モジュールに実装する例）
- data: DataProvider（市場データを返す）
- strategy: Strategy（シグナルを生成する）
- execution: Broker（注文を送る）
- monitoring: Monitor（ログ・状態監視）

例: strategy の簡易実装イメージ
```python
# src/kabusys/strategy/simple.py
class SimpleStrategy:
    def __init__(self, data_provider):
        self.data = data_provider

    def generate_signal(self):
        # 単純移動平均クロス等のロジックをここに実装
        # 戻り値例: {"symbol": "7203", "action": "BUY", "size": 100}
        pass
```

実行フローのイメージ:
1. DataProvider から最新データを取得
2. Strategy でシグナルを生成
3. Broker（Execution）により注文を送信
4. Monitor でログ・アラート記録

---

## 開発／拡張ガイド
- 新しい戦略は `src/kabusys/strategy/` にモジュールを追加してください。
- 証券会社 API との連携は `src/kabusys/execution/` にブローカーラッパーを実装してください（例: Kabuステーション HTTP/WebSocket）。
- データ取得（板・約定・OHLC 等）は `src/kabusys/data/` に実装。
- 監視やメトリクス出力は `src/kabusys/monitoring/` に実装。

テストや CI を導入する場合は `tests/` ディレクトリを作成し、pytest 等を使用してください。

実装テンプレート（例）:
- data/base.py に抽象 DataProvider クラス
- strategy/base.py に抽象 Strategy クラス
- execution/base.py に Broker 抽象クラス
- monitoring/base.py に Monitor 抽象クラス

---

## ディレクトリ構成
現在の主要ファイル構成（簡易表示）:
```
.
├─ src/
│  └─ kabusys/
│     ├─ __init__.py            # パッケージ初期化, __version__ 等
│     ├─ data/
│     │  └─ __init__.py
│     ├─ strategy/
│     │  └─ __init__.py
│     ├─ execution/
│     │  └─ __init__.py
│     └─ monitoring/
│        └─ __init__.py
```

将来的に追加するファイル例:
```
src/kabusys/data/base.py
src/kabusys/data/kabu_station.py
src/kabusys/strategy/base.py
src/kabusys/strategy/simple.py
src/kabusys/execution/base.py
src/kabusys/execution/kabu_broker.py
src/kabusys/monitoring/logger.py
config.yaml
requirements.txt
tests/
```

---

## 最後に / 注意点
- 本リポジトリは骨組み（テンプレート）です。実際の取引に用いる場合は、十分なテスト、リスク管理、法令遵守（金融商品取引法等）を行ってください。
- 実運用前にサンドボックス環境やデモ口座での検証を強く推奨します。

必要であれば、README に含めるサンプル実装（抽象クラスのテンプレートや、特定の証券 API との接続サンプル）を作成します。どの部分のサンプルが欲しいか教えてください。